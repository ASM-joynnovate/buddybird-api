from datetime import datetime, time, timedelta

from sqlalchemy import ARRAY, BigInteger, and_, case, cast, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import FeedbackSaveUnavailableError
from app.models import AppUpdate, Device, Feedback, User
from app.s3 import S3StorageClient
from app.schemas.base import FileDTO
from app.schemas.feedback import (
    BackofficeFeedbackDeviceDTO,
    BackofficeFeedbackDTO,
    BackofficeFeedbackListParams,
    BackofficeFeedbackUserDTO,
    CreateFeedbackRequest,
    FeedbackDTO,
)
from app.services.devices import VERSION_PATTERN
from app.services.users import SEOUL


def build_feedback_dto(feedback: Feedback) -> FeedbackDTO:
    return FeedbackDTO(
        id=feedback.id,
        user_id=feedback.user_id,
        device_id=feedback.device_id,
        message=feedback.message,
        app_version=feedback.app_version,
        created_at=feedback.created_at,
    )


@transactional(unavailable_error=FeedbackSaveUnavailableError)
async def create(*, db: AsyncSession, user: User, device: Device, data: CreateFeedbackRequest) -> FeedbackDTO:
    feedback = Feedback(user_id=user.id, device_id=device.id, message=data.message, app_version=device.app_version)

    db.add(feedback)
    await db.flush()

    return build_feedback_dto(feedback)


async def get_list(
    *, db: AsyncSession, storage: S3StorageClient, query: BackofficeFeedbackListParams
) -> tuple[list[BackofficeFeedbackDTO], int]:
    conditions = []

    if query.user_id is not None:
        conditions.append(Feedback.user_id == query.user_id)

    if query.keyword is not None:
        conditions.append(
            or_(
                Feedback.message.icontains(query.keyword, autoescape=True),
                User.nickname.icontains(query.keyword, autoescape=True),
                User.email.icontains(query.keyword, autoescape=True),
            )
        )

    if query.created_from is not None:
        conditions.append(Feedback.created_at >= datetime.combine(query.created_from, time(0), tzinfo=SEOUL))

    if query.created_to is not None:
        conditions.append(
            Feedback.created_at < datetime.combine(query.created_to + timedelta(days=1), time(0), tzinfo=SEOUL)
        )

    if query.app_version is not None:
        conditions.append(Feedback.app_version == query.app_version)

    if query.platform is not None:
        conditions.append(Device.platform == query.platform.value)

    if query.locale is not None:
        conditions.append(Device.locale == query.locale.value)

    stmt = (
        select(func.count())
        .select_from(Feedback)
        .join(User, User.id == Feedback.user_id)
        .join(Device, Device.id == Feedback.device_id)
        .where(*conditions)
        .execution_options(include_deleted=True)
    )
    total = await db.scalar(stmt)

    is_unsupported = case(
        (
            and_(
                Feedback.app_version.regexp_match(VERSION_PATTERN),
                AppUpdate.min_supported_version.regexp_match(VERSION_PATTERN),
            ),
            cast(func.string_to_array(Feedback.app_version, "."), ARRAY(BigInteger))
            < cast(func.string_to_array(AppUpdate.min_supported_version, "."), ARRAY(BigInteger)),
        ),
        else_=false(),
    )
    stmt = (
        select(Feedback, User, Device, is_unsupported.label("is_unsupported"))
        .select_from(Feedback)
        .join(User, User.id == Feedback.user_id)
        .join(Device, Device.id == Feedback.device_id)
        .outerjoin(AppUpdate, AppUpdate.platform == Device.platform)
        .where(*conditions)
        .order_by(Feedback.created_at.desc())
        .offset((query.page - 1) * query.count_by_page)
        .limit(query.count_by_page)
        .execution_options(include_deleted=True)
    )
    rows = (await db.execute(stmt)).all()
    items = []

    for row in rows:
        photo = None

        if row.User.photo_file is not None:
            photo = FileDTO(
                url=storage.generate_presigned_url(path=row.User.photo_file.object_key),
                status=row.User.photo_file.status,
            )

        items.append(
            BackofficeFeedbackDTO(
                **build_feedback_dto(row.Feedback).model_dump(),
                is_unsupported=row.is_unsupported,
                user=BackofficeFeedbackUserDTO(
                    nickname=row.User.nickname,
                    email=row.User.email,
                    is_anonymous=row.User.is_anonymous,
                    is_deleted=row.User.is_deleted,
                    photo_file=photo,
                ),
                device=BackofficeFeedbackDeviceDTO(
                    platform=row.Device.platform,
                    os_version=row.Device.os_version,
                    model=row.Device.model,
                    locale=row.Device.locale,
                ),
            )
        )

    return items, total
