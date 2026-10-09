import asyncio
import io
import logging
from datetime import UTC, datetime, time, timedelta
from urllib.parse import urlsplit
from uuid import UUID, uuid7
from zoneinfo import ZoneInfo

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import (
    ARRAY,
    BigInteger,
    DateTime,
    and_,
    asc,
    case,
    cast,
    desc,
    exists,
    false,
    func,
    not_,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import aggregate_order_by, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from app.db import transactional
from app.enums import (
    FileStatusEnum,
    SessionEndReasonEnum,
    SessionEventKindEnum,
    SessionStatusEnum,
    SortOrderEnum,
    UserIssueEnum,
    UserLastSessionEnum,
    UserSortEnum,
)
from app.errors import (
    DuplicateNicknameError,
    FileSizeExceededError,
    InvalidProfilePhotoError,
    UserSaveUnavailableError,
)
from app.models import (
    Device,
    File,
    Parrot,
    Session,
    SessionEvent,
    User,
    UserIdentity,
    UserSetting,
    UserWithdrawal,
)
from app.oauth.base import http_client
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import UploadDTO, UploadRequest
from app.schemas.devices import BackofficeLastSeenDeviceDTO
from app.schemas.parrots import BackofficeParrotDTO
from app.schemas.users import (
    BackofficeUserDailyDurationDTO,
    BackofficeUserDetailDTO,
    BackofficeUserDTO,
    BackofficeUserListItemDTO,
    BackofficeUserListParams,
    BackofficeUserParrotDTO,
    BackofficeUserSessionDTO,
    UpdateUserRequest,
    UserDTO,
)
from app.services import devices
from app.services.sessions import SESSION_COUNT
from app.services.settings import build_settings_dto
from app.services.withdrawals import build_backoffice_withdrawal_dto

logger = logging.getLogger(__name__)

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTO_PIXELS = 20_000_000
PHOTO_TYPES = {"image/jpeg", "image/png"}
SOCIAL_PHOTO_TYPES = {"image/jpeg": "profile.jpg", "image/png": "profile.png", "image/webp": "profile.webp"}
SOCIAL_PHOTO_HOSTS = {
    "google": {"googleusercontent.com", "lh3.googleusercontent.com"},
    "kakao": {"k.kakaocdn.net", "t1.kakaocdn.net", "t1.daumcdn.net"},
}
SEOUL = ZoneInfo("Asia/Seoul")
TODAY_START = func.timezone(
    SEOUL.key, func.date_trunc("day", func.timezone(SEOUL.key, func.now())), type_=DateTime(timezone=True)
)
LAST_SESSION_AT = (
    select(func.max(func.coalesce(Session.ended_at, func.now())))
    .where(Session.user_id == User.id, Session.is_deleted.is_(False))
    .scalar_subquery()
)
LAST_SESSION = case(
    (LAST_SESSION_AT >= TODAY_START, UserLastSessionEnum.TODAY.value),
    (LAST_SESSION_AT + timedelta(days=6) >= TODAY_START, UserLastSessionEnum.WITHIN_7_DAYS.value),
    (LAST_SESSION_AT + timedelta(days=29) >= TODAY_START, UserLastSessionEnum.WITHIN_30_DAYS.value),
    (LAST_SESSION_AT.is_not(None), UserLastSessionEnum.OVER_30_DAYS.value),
    else_=UserLastSessionEnum.NONE.value,
)
PUSHABLE = and_(
    func.coalesce(
        select(UserSetting.push_notification_enabled)
        .where(UserSetting.user_id == User.id)
        .correlate(User)
        .scalar_subquery(),
        true(),
    ),
    exists().where(Device.user_id == User.id, Device.push_token.is_not(None), Device.is_deleted.is_(False)),
)
ISSUE_SINCE = func.now() - timedelta(hours=24)
ISSUES = {
    UserIssueEnum.HEARTBEAT_EXPIRED: exists().where(
        Session.user_id == User.id,
        Session.ended_reason == SessionEndReasonEnum.HEARTBEAT_EXPIRED.value,
        Session.ended_at >= ISSUE_SINCE,
    ),
    UserIssueEnum.EMERGENCY_DETECTED: exists(
        select(SessionEvent.id)
        .join(Session, Session.id == SessionEvent.session_id)
        .where(
            Session.user_id == User.id,
            SessionEvent.kind == SessionEventKindEnum.EMERGENCY_DETECTED.value,
            SessionEvent.occurred_at >= ISSUE_SINCE,
        )
    ),
    UserIssueEnum.WITHDRAWAL_FAILED: exists().where(
        UserWithdrawal.user_id == User.id,
        UserWithdrawal.completed_at.is_(None),
        UserWithdrawal.last_error_code.is_not(None),
    ),
}


async def download_social_photo(*, url: str, provider: str) -> tuple[bytes, str, str] | None:
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname or ""
        allowed_hosts = SOCIAL_PHOTO_HOSTS.get(provider, ())
        disallowed = (
            parsed.scheme != "https"
            or hostname not in allowed_hosts
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        )

        if disallowed:
            return None

        async with asyncio.timeout(10), http_client.stream("GET", url) as response:
            response.raise_for_status()

            file_type = response.headers.get("content-type", "").partition(";")[0].lower()
            file_name = SOCIAL_PHOTO_TYPES.get(file_type)

            if file_name is None or int(response.headers.get("content-length", "0")) > MAX_PHOTO_BYTES:
                return None

            content = bytearray()

            async for chunk in response.aiter_bytes(64 * 1024):
                content.extend(chunk)

                if len(content) > MAX_PHOTO_BYTES:
                    return None
    except httpx.HTTPError, OSError, TimeoutError, ValueError:
        return None

    if not content:
        return None

    return bytes(content), file_name, file_type


async def prepare_uploaded_photo(content: bytes) -> bytes:
    def transform() -> bytes:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in {"JPEG", "PNG"} or source.width * source.height > MAX_PHOTO_PIXELS:
                raise ValueError

            image = ImageOps.exif_transpose(source)

            if "A" in image.getbands() or (image.mode == "P" and "transparency" in image.info):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85)

            return output.getvalue()

    try:
        return await asyncio.to_thread(transform)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidProfilePhotoError from exc


async def delete_uploaded_photo(*, storage: S3StorageClient, path: str, version_id: str) -> None:
    try:
        await storage.delete(path=path, version_id=version_id)
    except Exception:
        logger.exception("업로드된 프로필 사진 정리 실패")


async def get_uploading_photo_files(*, db: AsyncSession, file_ids: set[UUID]) -> dict[UUID, File]:
    if not file_ids:
        return {}

    stmt = (
        select(File)
        .where(
            File.id.in_(file_ids),
            or_(
                File.status == FileStatusEnum.REJECTED.value,
                and_(
                    File.status == FileStatusEnum.PENDING.value,
                    File.created_at > datetime.now(UTC) - timedelta(seconds=UPLOAD_URL_EXPIRES_IN),
                ),
            ),
        )
        .execution_options(include_deleted=True)
    )
    files = (await db.scalars(stmt)).all()

    return {file.id: file for file in files}


async def get_profile(*, db: AsyncSession, user: User, storage: S3StorageClient) -> UserDTO:
    uploading_photo_files = await get_uploading_photo_files(
        db=db,
        file_ids={user.uploading_photo_file_id} if user.uploading_photo_file_id is not None else set(),
    )
    uploading_photo_file = uploading_photo_files.get(user.uploading_photo_file_id)

    return UserDTO(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        photo_file=storage.generate_file_dto(file=user.photo_file),
        uploading_photo_file=storage.generate_file_dto(file=uploading_photo_file),
    )


def build_backoffice_user_dto(user: User) -> BackofficeUserDTO:
    return BackofficeUserDTO(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        is_anonymous=user.is_anonymous,
        is_deleted=user.is_deleted,
        created_at=user.created_at,
    )


async def get_backoffice_list(
    *, db: AsyncSession, storage: S3StorageClient, query: BackofficeUserListParams
) -> tuple[list[BackofficeUserListItemDTO], int]:
    now = datetime.now(UTC)
    today = now.astimezone(SEOUL).date()
    dates = [today - timedelta(days=offset) for offset in range(13, -1, -1)]
    recent_start = datetime.combine(dates[0], time(0), tzinfo=SEOUL)
    conditions = []

    if query.user_ids is not None:
        conditions.append(User.id.in_(query.user_ids))

    if query.keyword is not None:
        conditions.append(
            or_(
                User.nickname.icontains(query.keyword, autoescape=True),
                User.email.icontains(query.keyword, autoescape=True),
            )
        )

    if query.is_deleted is not None:
        conditions.append(User.is_deleted == query.is_deleted)

    if query.last_session is not None:
        conditions.append(query.last_session.value == LAST_SESSION)

    if query.created_from is not None:
        conditions.append(User.created_at >= datetime.combine(query.created_from, time(0), tzinfo=SEOUL))

    if query.created_to is not None:
        conditions.append(
            User.created_at < datetime.combine(query.created_to + timedelta(days=1), time(0), tzinfo=SEOUL)
        )

    if query.provider is not None:
        conditions.append(
            exists().where(UserIdentity.user_id == User.id, UserIdentity.provider == query.provider.value)
        )

    if query.is_anonymous is not None:
        conditions.append(User.is_anonymous == query.is_anonymous)

    if query.platform is not None:
        conditions.append(
            exists().where(
                Device.user_id == User.id,
                Device.platform == query.platform.value,
                Device.is_deleted.is_(False),
            )
        )

    if query.has_unsupported_device is not None:
        has_unsupported_device = exists(
            select(Device.id)
            .join(devices.MIN_SUPPORTED_APP_UPDATE, devices.MIN_SUPPORTED_APP_UPDATE.c.platform == Device.platform)
            .where(Device.user_id == User.id, Device.is_deleted.is_(False), devices.VERSION_UNSUPPORTED)
        )

        conditions.append(has_unsupported_device if query.has_unsupported_device else not_(has_unsupported_device))

    if query.is_pushable is not None:
        conditions.append(PUSHABLE if query.is_pushable else not_(PUSHABLE))

    is_announcement_enabled = func.coalesce(UserSetting.announcement_notification_enabled, true())
    is_marketing_enabled = func.coalesce(UserSetting.marketing_notification_enabled, false())

    if query.is_marketing_enabled is not None:
        conditions.append(is_marketing_enabled if query.is_marketing_enabled else not_(is_marketing_enabled))

    if query.issue is not None:
        conditions.append(ISSUES[query.issue])

    stmt = (
        select(func.count())
        .select_from(User)
        .outerjoin(UserSetting, UserSetting.user_id == User.id)
        .where(*conditions)
        .execution_options(include_deleted=True)
    )
    total = await db.scalar(stmt)

    session_end = func.coalesce(Session.ended_at, now)

    days = (
        func.generate_series(recent_start, recent_start + timedelta(days=13), timedelta(days=1))
        .table_valued("day_start")
        .render_derived()
    )
    day_end = days.c.day_start + timedelta(days=1)
    day_duration = (
        select(
            func.coalesce(
                func.sum(func.least(session_end, day_end) - func.greatest(Session.started_at, days.c.day_start)),
                timedelta(0),
            )
        )
        .where(
            Session.user_id == User.id,
            Session.is_deleted.is_(False),
            Session.started_at < day_end,
            session_end > days.c.day_start,
        )
        .correlate(User, days)
        .scalar_subquery()
    )
    daily_durations = (
        select(func.array_agg(aggregate_order_by(day_duration, days.c.day_start))).select_from(days).scalar_subquery()
    )

    parrot_count = (
        select(func.count())
        .select_from(Parrot)
        .where(Parrot.user_id == User.id, Parrot.is_deleted.is_(False))
        .scalar_subquery()
    )

    first_parrot = (
        select(Parrot.name, Parrot.species, Parrot.photo_file_id)
        .where(Parrot.user_id == User.id, Parrot.is_deleted.is_(False))
        .order_by(Parrot.created_at)
        .limit(1)
        .lateral()
    )

    parrot_photo_file = aliased(File, name="parrot_photo_file")
    running_session = aliased(Session)

    direction = asc if query.order == SortOrderEnum.ASC else desc
    order_by = [direction(User.created_at)]

    if query.sort == UserSortEnum.RECENT_DURATION:
        recent_duration = (
            select(
                func.coalesce(
                    func.sum(session_end - func.greatest(Session.started_at, recent_start)),
                    timedelta(0),
                )
            )
            .where(Session.user_id == User.id, Session.is_deleted.is_(False), session_end > recent_start)
            .scalar_subquery()
        )

        order_by = [direction(recent_duration), User.created_at.desc()]
    elif query.sort == UserSortEnum.SESSION_COUNT:
        order_by = [direction(SESSION_COUNT), User.created_at.desc()]
    elif query.sort == UserSortEnum.STATUS:
        order_by = [
            direction(running_session.id.is_not(None)),
            direction(devices.LAST_SEEN_DEVICE.c.last_seen_at).nulls_last(),
            User.created_at.desc(),
        ]
    elif query.sort == UserSortEnum.APP_VERSION:
        version_numbers = case(
            (
                devices.LAST_SEEN_DEVICE.c.app_version.regexp_match(devices.VERSION_PATTERN),
                cast(func.string_to_array(devices.LAST_SEEN_DEVICE.c.app_version, "."), ARRAY(BigInteger)),
            )
        )

        order_by = [direction(version_numbers).nulls_last(), User.created_at.desc()]
    elif query.sort == UserSortEnum.PARROT_COUNT:
        order_by = [direction(parrot_count), User.created_at.desc()]

    stmt = (
        select(
            User,
            first_parrot.c.name.label("parrot_name"),
            first_parrot.c.species.label("parrot_species"),
            parrot_photo_file,
            parrot_count.label("parrot_count"),
            running_session.id.label("running_session_id"),
            running_session.current_phase,
            devices.LAST_SEEN_DEVICE.c.platform,
            devices.LAST_SEEN_DEVICE.c.app_version,
            devices.LAST_SEEN_DEVICE.c.last_seen_at,
            devices.LAST_SEEN_DEVICE.c.is_unsupported,
            devices.DEVICE_COUNT.label("device_count"),
            SESSION_COUNT.label("session_count"),
            daily_durations.label("daily_durations"),
            PUSHABLE.label("is_pushable"),
            is_announcement_enabled.label("is_announcement_enabled"),
            is_marketing_enabled.label("is_marketing_enabled"),
        )
        .select_from(User)
        .options(joinedload(User.photo_file))
        .outerjoin(UserSetting, UserSetting.user_id == User.id)
        .outerjoin(first_parrot, true())
        .outerjoin(parrot_photo_file, parrot_photo_file.id == first_parrot.c.photo_file_id)
        .outerjoin(
            running_session,
            and_(
                running_session.user_id == User.id,
                running_session.status == SessionStatusEnum.RUNNING.value,
                running_session.is_deleted.is_(False),
            ),
        )
        .outerjoin(devices.LAST_SEEN_DEVICE, true())
        .where(*conditions)
        .order_by(*order_by)
        .offset((query.page - 1) * query.count_by_page)
        .limit(query.count_by_page)
        .execution_options(include_deleted=True)
    )
    rows = (await db.execute(stmt)).all()

    items = [
        BackofficeUserListItemDTO(
            **build_backoffice_user_dto(row.User).model_dump(),
            photo_file=storage.generate_file_dto(file=row.User.photo_file),
            first_parrot=BackofficeUserParrotDTO(
                name=row.parrot_name,
                species=row.parrot_species,
                photo_file=storage.generate_file_dto(file=row.parrot_photo_file),
            )
            if row.parrot_name is not None
            else None,
            parrot_count=row.parrot_count,
            running_session=BackofficeUserSessionDTO(current_phase=row.current_phase)
            if row.running_session_id is not None
            else None,
            last_seen_device=BackofficeLastSeenDeviceDTO(
                platform=row.platform,
                app_version=row.app_version,
                is_unsupported=row.is_unsupported,
                last_seen_at=row.last_seen_at,
            )
            if row.platform is not None
            else None,
            device_count=row.device_count,
            session_count=row.session_count,
            daily_durations=[
                BackofficeUserDailyDurationDTO(date=date, duration_ms=duration // timedelta(milliseconds=1))
                for date, duration in zip(dates, row.daily_durations, strict=True)
            ],
            is_pushable=row.is_pushable,
            is_announcement_enabled=row.is_announcement_enabled,
            is_marketing_enabled=row.is_marketing_enabled,
        )
        for row in rows
    ]

    return items, total


async def get_backoffice_detail(*, db: AsyncSession, storage: S3StorageClient, user: User) -> BackofficeUserDetailDTO:
    setting = await db.get(UserSetting, user.id)
    withdrawal = await db.get(UserWithdrawal, user.id)

    stmt = select(UserIdentity.provider).where(UserIdentity.user_id == user.id).order_by(UserIdentity.created_at)
    providers = (await db.scalars(stmt)).all()

    stmt = (
        select(Parrot)
        .where(Parrot.user_id == user.id, Parrot.is_deleted.is_(False))
        .order_by(Parrot.created_at)
        .execution_options(include_deleted=True)
    )
    parrots = (await db.scalars(stmt)).all()

    return BackofficeUserDetailDTO(
        **build_backoffice_user_dto(user).model_dump(),
        photo_file=storage.generate_file_dto(file=user.photo_file),
        providers=providers,
        settings=build_settings_dto(setting) if setting is not None else None,
        parrots=[
            BackofficeParrotDTO(
                id=parrot.id,
                name=parrot.name,
                species=parrot.species,
                birthdate=parrot.birthdate,
                photo_file=storage.generate_file_dto(file=parrot.photo_file),
                created_at=parrot.created_at,
            )
            for parrot in parrots
        ],
        devices=await devices.get_backoffice_list(db=db, user=user),
        withdrawal=build_backoffice_withdrawal_dto(withdrawal) if withdrawal is not None else None,
    )


async def save_identities(*, db: AsyncSession, user_id: UUID, providers: list[str]) -> None:
    if not providers:
        return

    await db.execute(
        insert(UserIdentity)
        .values([{"user_id": user_id, "provider": provider} for provider in providers])
        .on_conflict_do_nothing()
    )


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_profile(*, db: AsyncSession, user: User, data: UpdateUserRequest) -> None:
    changes = data.model_dump(exclude_unset=True)

    if "nickname" not in changes:
        return

    user.nickname = changes["nickname"]

    try:
        await db.flush()
    except IntegrityError as exc:
        raise DuplicateNicknameError from exc


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_photo(*, db: AsyncSession, storage: S3StorageClient, user: User, data: UploadRequest) -> UploadDTO:
    if data.content_type not in PHOTO_TYPES:
        raise InvalidProfilePhotoError

    if data.file_size > MAX_PHOTO_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()

    photo_file = File(
        id=file_id,
        file_name="profile.jpg",
        file_path=f"user/{user.id}/profile/{file_id}",
        file_size=data.file_size,
        file_type="image/jpeg",
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(photo_file)

    await db.flush()

    user.uploading_photo_file_id = photo_file.id

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=f"upload/{photo_file.object_key}",
        content_type=data.content_type,
        file_size=data.file_size,
    )


@transactional(unavailable_error=UserSaveUnavailableError)
async def delete_photo(*, db: AsyncSession, user: User) -> None:
    old_file = user.photo_file

    if old_file is None:
        return

    user.photo_file = None
    old_file.is_deleted = True

    await db.flush()
