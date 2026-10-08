import logging
from datetime import UTC, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, true, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app import sqs
from app.config import config
from app.db import session_factory, transactional
from app.enums import (
    OAuthProviderEnum,
    WithdrawalProgressEnum,
    WithdrawalStatusEnum,
    WithdrawalStepEnum,
    WithdrawalStepStatusEnum,
)
from app.errors import AuthenticationError, WithdrawalOperationError, WithdrawalSaveUnavailableError
from app.models import (
    Feedback,
    File,
    Session,
    User,
    UserOAuthCredential,
    UserWithdrawal,
    UserWithdrawalFailure,
)
from app.oauth.apple import revoke_apple
from app.oauth.base import SocialIdentity, decrypt_credentials, encrypt_credentials
from app.oauth.google import revoke_google
from app.oauth.kakao import unlink_kakao
from app.oauth.supabase import delete_supabase_user, get_admin_social_identities, get_social_identities
from app.s3 import S3StorageClient
from app.schemas.devices import BackofficeLastSeenDeviceDTO
from app.schemas.withdrawals import (
    BackofficeWithdrawalDTO,
    BackofficeWithdrawalListItemDTO,
    BackofficeWithdrawalListParams,
    BackofficeWithdrawalProviderDTO,
    BackofficeWithdrawalStepDTO,
    BackofficeWithdrawalUserDTO,
    WithdrawalDTO,
)
from app.services.devices import DEVICE_COUNT, LAST_SEEN_DEVICE
from app.services.sessions import SESSION_COUNT

logger = logging.getLogger(__name__)

SEOUL = ZoneInfo("Asia/Seoul")


def build_backoffice_withdrawal_dto(withdrawal: UserWithdrawal) -> BackofficeWithdrawalDTO:
    return BackofficeWithdrawalDTO(
        user_id=withdrawal.user_id,
        providers=[
            BackofficeWithdrawalProviderDTO(provider=provider, status=getattr(withdrawal, f"{provider}_status"))
            for provider in OAuthProviderEnum
        ],
        attempt_count=withdrawal.attempt_count,
        last_error_code=withdrawal.last_error_code,
        next_attempt_at=withdrawal.next_attempt_at,
        completed_at=withdrawal.completed_at,
        created_at=withdrawal.created_at,
    )


async def get_backoffice_list(
    *, db: AsyncSession, storage: S3StorageClient, query: BackofficeWithdrawalListParams
) -> tuple[list[BackofficeWithdrawalListItemDTO], int]:
    stmt = select(UserWithdrawal)

    if query.is_completed is True:
        stmt = stmt.where(UserWithdrawal.completed_at.is_not(None))
    elif query.is_completed is False:
        stmt = stmt.where(UserWithdrawal.completed_at.is_(None))

    if query.created_from is not None:
        stmt = stmt.where(UserWithdrawal.created_at >= datetime.combine(query.created_from, time(0), tzinfo=SEOUL))

    if query.created_to is not None:
        stmt = stmt.where(
            UserWithdrawal.created_at < datetime.combine(query.created_to + timedelta(days=1), time(0), tzinfo=SEOUL)
        )

    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))

    last_session_started_at = (
        select(func.max(Session.started_at))
        .where(Session.user_id == User.id, Session.is_deleted.is_(False))
        .scalar_subquery()
    )
    feedback_count = select(func.count()).select_from(Feedback).where(Feedback.user_id == User.id).scalar_subquery()
    last_feedback_message = (
        select(Feedback.message)
        .where(Feedback.user_id == User.id)
        .order_by(Feedback.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )

    stmt = (
        stmt.add_columns(
            User,
            SESSION_COUNT.label("session_count"),
            last_session_started_at.label("last_session_started_at"),
            LAST_SEEN_DEVICE.c.platform,
            LAST_SEEN_DEVICE.c.app_version,
            LAST_SEEN_DEVICE.c.last_seen_at,
            LAST_SEEN_DEVICE.c.is_unsupported,
            DEVICE_COUNT.label("device_count"),
            feedback_count.label("feedback_count"),
            last_feedback_message.label("last_feedback_message"),
        )
        .join(User, User.id == UserWithdrawal.user_id)
        .options(joinedload(User.photo_file))
        .outerjoin(LAST_SEEN_DEVICE, true())
        .order_by(UserWithdrawal.created_at.desc())
        .offset((query.page - 1) * query.count_by_page)
        .limit(query.count_by_page)
        .execution_options(include_deleted=True)
    )
    rows = (await db.execute(stmt)).all()
    items = []

    for row in rows:
        withdrawal = row.UserWithdrawal
        status = WithdrawalProgressEnum.STOPPED

        if withdrawal.completed_at is not None:
            status = WithdrawalProgressEnum.COMPLETED
        elif withdrawal.last_error_code is None:
            status = WithdrawalProgressEnum.RUNNING
        elif withdrawal.next_attempt_at is not None:
            status = WithdrawalProgressEnum.RETRYING

        step_statuses = {
            WithdrawalStepEnum.APPLE: withdrawal.apple_status,
            WithdrawalStepEnum.GOOGLE: withdrawal.google_status,
            WithdrawalStepEnum.KAKAO: withdrawal.kakao_status,
            WithdrawalStepEnum.ACCOUNT: WithdrawalStatusEnum.COMPLETED.value
            if withdrawal.completed_at is not None
            else WithdrawalStatusEnum.PENDING.value,
        }
        pending_status = (
            WithdrawalStepStatusEnum.FAILED
            if withdrawal.last_error_code is not None
            else WithdrawalStepStatusEnum.RUNNING
        )
        steps = []

        for step, step_status in step_statuses.items():
            if step_status == WithdrawalStatusEnum.NOT_REQUIRED.value:
                continue

            if step_status == WithdrawalStatusEnum.PENDING.value:
                steps.append(BackofficeWithdrawalStepDTO(step=step, status=pending_status))

                pending_status = WithdrawalStepStatusEnum.WAITING
            else:
                steps.append(BackofficeWithdrawalStepDTO(step=step, status=step_status))

        items.append(
            BackofficeWithdrawalListItemDTO(
                **build_backoffice_withdrawal_dto(withdrawal).model_dump(),
                status=status,
                steps=steps,
                user=BackofficeWithdrawalUserDTO(
                    nickname=row.User.nickname,
                    email=row.User.email,
                    is_anonymous=row.User.is_anonymous,
                    photo_file=storage.generate_file_dto(file=row.User.photo_file),
                    created_at=row.User.created_at,
                    session_count=row.session_count,
                    last_session_started_at=row.last_session_started_at,
                    last_seen_device=BackofficeLastSeenDeviceDTO(
                        platform=row.platform,
                        app_version=row.app_version,
                        is_unsupported=row.is_unsupported,
                        last_seen_at=row.last_seen_at,
                    )
                    if row.platform is not None
                    else None,
                    device_count=row.device_count,
                    feedback_count=row.feedback_count,
                    last_feedback_message=row.last_feedback_message,
                ),
            )
        )

    return items, total


async def request_withdrawal(*, db: AsyncSession, auth_user_id: UUID, access_token: str) -> WithdrawalDTO:
    identities = await get_social_identities(auth_user_id=auth_user_id, access_token=access_token)

    return await save_withdrawal(db=db, auth_user_id=auth_user_id, identities=identities)


async def request_backoffice_withdrawal(*, db: AsyncSession, auth_user_id: UUID) -> WithdrawalDTO:
    identities = await get_admin_social_identities(auth_user_id)

    return await save_withdrawal(db=db, auth_user_id=auth_user_id, identities=identities)


@transactional(unavailable_error=WithdrawalSaveUnavailableError)
async def save_withdrawal(*, db: AsyncSession, auth_user_id: UUID, identities: list[SocialIdentity]) -> WithdrawalDTO:
    user = await db.scalar(
        select(User).where(User.auth_user_id == auth_user_id).execution_options(include_deleted=True)
    )

    if user is None:
        raise AuthenticationError

    existing = await db.get(UserWithdrawal, user.id)

    if existing is not None:
        return WithdrawalDTO(user_id=user.id)

    if user.is_deleted:
        raise AuthenticationError

    credentials = list(
        (await db.scalars(select(UserOAuthCredential).where(UserOAuthCredential.user_id == user.id))).all()
    )

    try:
        providers = {item.provider for item in identities} | {OAuthProviderEnum(item.provider) for item in credentials}
        statuses = {
            provider: WithdrawalStatusEnum.PENDING if provider in providers else WithdrawalStatusEnum.NOT_REQUIRED
            for provider in (OAuthProviderEnum.GOOGLE, OAuthProviderEnum.APPLE)
        }

        for identity in identities:
            if identity.provider not in statuses:
                continue

            confirmed = any(
                item.identity_id == identity.identity_id
                and item.provider == identity.provider.value
                and decrypt_credentials(item.credentials_ciphertext)["subject"] == identity.subject
                for item in credentials
            )

            if not confirmed:
                statuses[identity.provider] = WithdrawalStatusEnum.UNCONFIRMED

        kakao_ids = sorted({item.subject for item in identities if item.provider == OAuthProviderEnum.KAKAO})

        if any(not item.isascii() or not item.isdecimal() or not 0 < int(item) < 2**63 for item in kakao_ids):
            raise WithdrawalSaveUnavailableError

        kakao_user_ids_ciphertext = encrypt_credentials(kakao_ids) if kakao_ids else None
    except WithdrawalOperationError, KeyError, TypeError, ValueError:
        raise WithdrawalSaveUnavailableError from None

    db.add(
        UserWithdrawal(
            user_id=user.id,
            google_status=statuses[OAuthProviderEnum.GOOGLE].value,
            apple_status=statuses[OAuthProviderEnum.APPLE].value,
            kakao_status=WithdrawalStatusEnum.PENDING.value if kakao_ids else WithdrawalStatusEnum.NOT_REQUIRED.value,
            kakao_user_ids_ciphertext=kakao_user_ids_ciphertext,
            next_attempt_at=datetime.now(UTC),
        )
    )

    user.is_deleted = True

    await db.execute(
        update(File)
        .where(File.file_path.startswith(f"user/{user.id}/"))
        .values(is_deleted=True)
        .execution_options(include_deleted=True)
    )

    return WithdrawalDTO(user_id=user.id)


async def process_withdrawal_step(*, withdrawal: UserWithdrawal, user: User, db: AsyncSession) -> None:
    if not user.is_deleted:
        raise WithdrawalOperationError("withdrawal_user_not_deleted")

    credential = await db.scalar(
        select(UserOAuthCredential)
        .where(UserOAuthCredential.user_id == user.id)
        .order_by(UserOAuthCredential.provider, UserOAuthCredential.identity_id, UserOAuthCredential.client_id)
        .limit(1)
    )

    if credential is not None:
        data = decrypt_credentials(credential.credentials_ciphertext)
        invalid = (
            not isinstance(data, dict)
            or not isinstance(data.get("subject"), str)
            or not data["subject"]
            or not isinstance(data.get("refresh_token"), str)
            or not data["refresh_token"]
        )

        if invalid:
            raise WithdrawalOperationError("credentials_invalid")

        provider = OAuthProviderEnum(credential.provider)
        result = WithdrawalStatusEnum.COMPLETED

        if provider == OAuthProviderEnum.GOOGLE:
            result = await revoke_google(data["refresh_token"])
        else:
            await revoke_apple(client_id=credential.client_id, refresh_token=data["refresh_token"])

        await db.delete(credential)
        await db.flush()

        remaining = await db.scalar(
            select(UserOAuthCredential.user_id)
            .where(UserOAuthCredential.user_id == user.id, UserOAuthCredential.provider == provider.value)
            .limit(1)
        )

        if provider == OAuthProviderEnum.GOOGLE:
            if result == WithdrawalStatusEnum.UNCONFIRMED:
                withdrawal.google_status = WithdrawalStatusEnum.UNCONFIRMED.value
            elif remaining is None and withdrawal.google_status != WithdrawalStatusEnum.UNCONFIRMED.value:
                withdrawal.google_status = WithdrawalStatusEnum.COMPLETED.value
        elif remaining is None and withdrawal.apple_status != WithdrawalStatusEnum.UNCONFIRMED.value:
            withdrawal.apple_status = WithdrawalStatusEnum.COMPLETED.value

        return

    if withdrawal.kakao_user_ids_ciphertext is not None:
        user_ids = decrypt_credentials(withdrawal.kakao_user_ids_ciphertext)
        invalid = (
            not isinstance(user_ids, list)
            or not user_ids
            or any(
                not isinstance(item, str) or not item.isascii() or not item.isdecimal() or not 0 < int(item) < 2**63
                for item in user_ids
            )
        )

        if invalid:
            raise WithdrawalOperationError("kakao_credentials_invalid")

        await unlink_kakao(user_ids[0])

        remaining_ids = user_ids[1:]
        withdrawal.kakao_user_ids_ciphertext = encrypt_credentials(remaining_ids) if remaining_ids else None

        if not remaining_ids:
            withdrawal.kakao_status = WithdrawalStatusEnum.COMPLETED.value

        return

    pending = any(
        WithdrawalStatusEnum(status) == WithdrawalStatusEnum.PENDING
        for status in (withdrawal.google_status, withdrawal.apple_status, withdrawal.kakao_status)
    )

    if pending:
        raise WithdrawalOperationError("withdrawal_credentials_missing")

    await delete_supabase_user(user.auth_user_id)

    withdrawal.completed_at = datetime.now(UTC)
    withdrawal.next_attempt_at = None


def record_failure(*, db: AsyncSession, withdrawal: UserWithdrawal, error: WithdrawalOperationError) -> None:
    withdrawal.attempt_count += 1
    withdrawal.last_error_code = error.error_code
    withdrawal.next_attempt_at = (
        datetime.now(UTC) + timedelta(seconds=min(60 * 2 ** min(withdrawal.attempt_count - 1, 6), 3600))
        if error.retryable
        else None
    )

    db.add(UserWithdrawalFailure(user_id=withdrawal.user_id, error_code=error.error_code))


async def process_user_withdrawal(user_id: UUID) -> None:
    while True:
        version_id = None

        try:
            async with session_factory() as db, db.begin():
                user = await db.scalar(
                    select(User)
                    .where(User.id == user_id)
                    .execution_options(include_deleted=True)
                    .with_for_update(skip_locked=True)
                )

                if user is None:
                    return

                withdrawal = await db.scalar(
                    select(UserWithdrawal).where(UserWithdrawal.user_id == user_id).with_for_update()
                )
                skipped = (
                    withdrawal is None
                    or withdrawal.completed_at is not None
                    or withdrawal.next_attempt_at is None
                    or withdrawal.next_attempt_at > datetime.now(UTC)
                )

                if skipped:
                    return

                version_id = withdrawal.version_id

                try:
                    await process_withdrawal_step(withdrawal=withdrawal, user=user, db=db)
                except WithdrawalOperationError as exc:
                    record_failure(db=db, withdrawal=withdrawal, error=exc)

                    return

                withdrawal.last_error_code = None

                if withdrawal.completed_at is not None:
                    return
        except Exception as exc:
            db_unavailable = isinstance(exc, (SQLAlchemyError, OSError))
            error = WithdrawalOperationError(
                "withdrawal_db_unavailable" if db_unavailable else "withdrawal_internal_error",
                retryable=db_unavailable,
            )

            try:
                async with session_factory() as db, db.begin():
                    withdrawal = await db.scalar(
                        select(UserWithdrawal)
                        .where(UserWithdrawal.user_id == user_id)
                        .with_for_update(skip_locked=True)
                    )
                    recordable = (
                        withdrawal is not None
                        and withdrawal.completed_at is None
                        and withdrawal.next_attempt_at is not None
                        and (version_id is None or withdrawal.version_id == version_id)
                    )

                    if recordable:
                        record_failure(db=db, withdrawal=withdrawal, error=error)
            except Exception:
                logger.exception("탈퇴 처리 오류 기록 실패")

            logger.warning("탈퇴 처리 중단: %s", error.error_code)

            return


async def enqueue_withdrawal(*user_ids: UUID) -> None:
    for user_id in user_ids:
        try:
            await sqs.send(
                queue_url=config.SQS_WITHDRAWAL_QUEUE_URL,
                body={"type": "withdrawal.process", "user_id": str(user_id)},
            )
        except Exception:
            logger.warning("탈퇴 작업 큐 전달 실패; DB 기록에서 재전달 예정")


async def dispatch_due_withdrawals() -> None:
    after = None
    due_at = datetime.now(UTC)

    while True:
        async with session_factory() as db:
            query = select(UserWithdrawal.user_id).where(
                UserWithdrawal.completed_at.is_(None), UserWithdrawal.next_attempt_at <= due_at
            )

            if after is not None:
                query = query.where(UserWithdrawal.user_id > after)

            user_ids = list((await db.scalars(query.order_by(UserWithdrawal.user_id).limit(100))).all())

        if not user_ids:
            return

        await enqueue_withdrawal(*user_ids)

        after = user_ids[-1]
