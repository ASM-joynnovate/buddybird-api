from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import ARRAY, BigInteger, Date, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import (
    NotificationKindEnum,
    SessionActorEnum,
    SessionEventKindEnum,
    SessionPhaseEnum,
    SessionStatusEnum,
    SoundJudgmentStatusEnum,
)
from app.models import (
    Announcement,
    AnnouncementRead,
    AppUpdate,
    Device,
    Feedback,
    I18n,
    Notification,
    Session,
    SessionEvent,
    SessionSound,
    User,
    UserWithdrawal,
)
from app.schemas.base import I18nDTO
from app.schemas.dashboard import (
    DashboardAnnouncementDTO,
    DashboardDailyCountDTO,
    DashboardDevicesDTO,
    DashboardDeviceVersionDTO,
    DashboardDTO,
    DashboardFeedbackDTO,
    DashboardLiveDTO,
    DashboardLiveHourlyDTO,
    DashboardLiveLast24HoursDTO,
    DashboardLivePhaseDTO,
    DashboardLiveRunningDTO,
    DashboardLiveSessionsDTO,
    DashboardLiveTodayDTO,
    DashboardLiveWithdrawalsDTO,
    DashboardNotificationDTO,
    DashboardNotificationKindDTO,
    DashboardNotificationsDTO,
    DashboardParams,
    DashboardSessionsDTO,
    DashboardUsersDTO,
    DashboardWithdrawalsDTO,
)

SEOUL = ZoneInfo("Asia/Seoul")


async def get_dashboard(*, db: AsyncSession, query: DashboardParams) -> DashboardDTO:
    now = datetime.now(UTC)
    dates = [query.date_from + timedelta(days=offset) for offset in range((query.date_to - query.date_from).days + 1)]
    period_start = datetime.combine(query.date_from, time(0), tzinfo=SEOUL)
    period_end = period_start + timedelta(days=len(dates))
    previous_start = period_start - timedelta(days=len(dates))

    duration = Session.ended_at - Session.started_at
    in_period = Session.started_at >= period_start
    stmt = (
        select(
            func.count().filter(in_period).label("session_count"),
            func.count().filter(Session.started_at < period_start).label("previous_session_count"),
            func.count(Session.user_id.distinct()).filter(in_period).label("active_user_count"),
            func.coalesce(func.sum(duration).filter(in_period), timedelta(0)).label("duration"),
            func.avg(duration).filter(in_period).label("average_duration"),
        )
        .select_from(Session)
        .where(Session.started_at >= previous_start, Session.started_at < period_end)
        .execution_options(include_deleted=True)
    )
    session_totals = (await db.execute(stmt)).one()

    stmt = (
        select(
            func.count().filter(User.is_deleted.is_(False)).label("total_count"),
            func.count().filter(User.created_at >= period_start, User.created_at < period_end).label("signup_count"),
            func.count()
            .filter(User.created_at >= previous_start, User.created_at < period_start)
            .label("previous_signup_count"),
        )
        .select_from(User)
        .execution_options(include_deleted=True)
    )
    user_counts = (await db.execute(stmt)).one()

    stmt = (
        select(func.count())
        .select_from(UserWithdrawal)
        .where(UserWithdrawal.created_at >= period_start, UserWithdrawal.created_at < period_end)
    )
    withdrawal_count = await db.scalar(stmt)

    stmt = (
        select(
            func.count().filter(Feedback.created_at >= period_start).label("feedback_count"),
            func.count().filter(Feedback.created_at < period_start).label("previous_feedback_count"),
        )
        .select_from(Feedback)
        .where(Feedback.created_at >= previous_start, Feedback.created_at < period_end)
    )
    feedback_counts = (await db.execute(stmt)).one()

    daily_counts = {}

    for column in (Session.started_at, User.created_at, UserWithdrawal.created_at):
        local_date = cast(func.timezone(SEOUL.key, column), Date)
        stmt = (
            select(local_date, func.count())
            .where(column >= period_start, column < period_end)
            .group_by(local_date)
            .execution_options(include_deleted=True)
        )
        daily_counts[column.class_] = dict((await db.execute(stmt)).all())

    stmt = (
        select(Notification.kind, func.count(), func.count(Notification.read_at))
        .where(
            Notification.sent_at >= period_start,
            Notification.sent_at < period_end,
            Notification.sent_at <= now,
        )
        .group_by(Notification.kind)
    )
    notification_counts = (await db.execute(stmt)).all()

    sent_at = func.min(Notification.sent_at)
    stmt = (
        select(
            Notification.kind,
            I18n.ko_kr,
            I18n.en_us,
            sent_at.label("sent_at"),
            func.count().label("recipient_count"),
            func.count(Notification.read_at).label("read_count"),
        )
        .join(I18n, I18n.id == Notification.title_i18n_id)
        .where(Notification.kind != NotificationKindEnum.REPORT.value)
        .group_by(Notification.kind, I18n.id)
        .limit(5)
    )
    notification_lists = {}

    for name, condition, order in (
        ("recent", Notification.sent_at <= now, sent_at.desc()),
        ("scheduled", Notification.sent_at > now, sent_at),
    ):
        rows = (await db.execute(stmt.where(condition).order_by(order))).all()
        notification_lists[name] = [
            DashboardNotificationDTO(
                kind=row.kind,
                title=I18nDTO(ko_kr=row.ko_kr, en_us=row.en_us),
                sent_at=row.sent_at,
                recipient_count=row.recipient_count,
                read_count=row.read_count,
            )
            for row in rows
        ]

    stmt = (
        select(
            Announcement.id,
            I18n.ko_kr,
            I18n.en_us,
            Announcement.starts_at,
            func.count(User.id).label("read_count"),
        )
        .select_from(Announcement)
        .join(I18n, I18n.id == Announcement.title_i18n_id)
        .outerjoin(AnnouncementRead, AnnouncementRead.announcement_id == Announcement.id)
        .outerjoin(User, User.id == AnnouncementRead.user_id)
        .where(or_(Announcement.ends_at.is_(None), Announcement.ends_at > now))
        .group_by(Announcement.id, I18n.id)
        .order_by(Announcement.starts_at.desc())
        .limit(5)
    )
    announcements = (await db.execute(stmt)).all()

    stmt = select(Device.app_version, func.count()).join(User, User.id == Device.user_id).group_by(Device.app_version)
    device_versions = (await db.execute(stmt)).all()

    version_pattern = r"^[0-9]+(\.[0-9]+)*$"
    stmt = (
        select(func.count())
        .select_from(Device)
        .join(User, User.id == Device.user_id)
        .join(AppUpdate, AppUpdate.platform == Device.platform)
        .where(
            case(
                (
                    and_(
                        Device.app_version.regexp_match(version_pattern),
                        AppUpdate.min_supported_version.regexp_match(version_pattern),
                    ),
                    cast(func.string_to_array(Device.app_version, "."), ARRAY(BigInteger))
                    < cast(func.string_to_array(AppUpdate.min_supported_version, "."), ARRAY(BigInteger)),
                )
            )
        )
    )
    unsupported_device_count = await db.scalar(stmt)

    return DashboardDTO(
        sessions=DashboardSessionsDTO(
            count=session_totals.session_count,
            previous_count=session_totals.previous_session_count,
            duration_ms=session_totals.duration // timedelta(milliseconds=1),
            average_duration_ms=session_totals.average_duration // timedelta(milliseconds=1)
            if session_totals.average_duration is not None
            else None,
            daily=[DashboardDailyCountDTO(date=date, count=daily_counts[Session].get(date, 0)) for date in dates],
        ),
        users=DashboardUsersDTO(
            total_count=user_counts.total_count,
            active_count=session_totals.active_user_count,
            signup_count=user_counts.signup_count,
            previous_signup_count=user_counts.previous_signup_count,
            daily_signups=[DashboardDailyCountDTO(date=date, count=daily_counts[User].get(date, 0)) for date in dates],
        ),
        withdrawals=DashboardWithdrawalsDTO(
            count=withdrawal_count,
            daily=[
                DashboardDailyCountDTO(date=date, count=daily_counts[UserWithdrawal].get(date, 0)) for date in dates
            ],
        ),
        feedback=DashboardFeedbackDTO(
            count=feedback_counts.feedback_count,
            previous_count=feedback_counts.previous_feedback_count,
        ),
        notifications=DashboardNotificationsDTO(
            kinds=[
                DashboardNotificationKindDTO(kind=kind, sent_count=sent_count, read_count=read_count)
                for kind, sent_count, read_count in notification_counts
            ],
            recent=notification_lists["recent"],
            scheduled=notification_lists["scheduled"],
        ),
        announcements=[
            DashboardAnnouncementDTO(
                id=announcement.id,
                title=I18nDTO(ko_kr=announcement.ko_kr, en_us=announcement.en_us),
                starts_at=announcement.starts_at,
                read_count=announcement.read_count,
            )
            for announcement in announcements
        ],
        devices=DashboardDevicesDTO(
            versions=[
                DashboardDeviceVersionDTO(app_version=app_version, count=count)
                for app_version, count in device_versions
            ],
            unsupported_count=unsupported_device_count,
        ),
    )


async def get_live(*, db: AsyncSession) -> DashboardLiveDTO:
    now = datetime.now(UTC)
    since = now - timedelta(hours=24)
    today_start = now.astimezone(SEOUL).replace(hour=0, minute=0, second=0, microsecond=0)

    is_running = Session.status == SessionStatusEnum.RUNNING.value
    stmt = select(Session.current_phase, func.count()).where(is_running).group_by(Session.current_phase)
    phase_counts = dict((await db.execute(stmt)).all())

    stmt = select(
        func.count().filter(is_running).label("running_count"),
        func.avg(now - Session.started_at).filter(is_running).label("running_duration"),
        func.count().filter(Session.started_at >= today_start).label("started_count"),
        func.count().filter(Session.ended_at >= today_start).label("ended_count"),
        func.count()
        .filter(
            Session.ended_by == SessionActorEnum.SERVER.value,
            Session.ended_at == func.coalesce(Session.last_heartbeat_at, Session.started_at),
            Session.ended_at >= since,
        )
        .label("heartbeat_expired_count"),
    ).select_from(Session)
    session_counts = (await db.execute(stmt)).one()

    hours = func.generate_series(today_start, now, timedelta(hours=1)).table_valued("hour_start").render_derived()
    stmt = (
        select(hours.c.hour_start, func.count(Session.id))
        .select_from(hours)
        .outerjoin(
            Session,
            and_(
                Session.started_at < hours.c.hour_start + timedelta(hours=1),
                func.coalesce(Session.ended_at, now) > hours.c.hour_start,
            ),
        )
        .group_by(hours.c.hour_start)
        .order_by(hours.c.hour_start)
    )
    hourly_counts = (await db.execute(stmt)).all()

    stmt = (
        select(func.count())
        .select_from(SessionEvent)
        .where(
            SessionEvent.kind == SessionEventKindEnum.EMERGENCY_DETECTED.value,
            SessionEvent.occurred_at >= since,
        )
    )
    emergency_detected_count = await db.scalar(stmt)

    stmt = (
        select(func.count())
        .select_from(SessionSound)
        .where(
            SessionSound.judgment_status == SoundJudgmentStatusEnum.FAILED.value,
            SessionSound.updated_at >= since,
        )
    )
    judgment_failed_count = await db.scalar(stmt)

    stmt = (
        select(func.count())
        .select_from(UserWithdrawal)
        .where(UserWithdrawal.completed_at.is_(None), UserWithdrawal.last_error_code.is_not(None))
    )
    failed_withdrawal_count = await db.scalar(stmt)

    return DashboardLiveDTO(
        generated_at=now,
        sessions=DashboardLiveSessionsDTO(
            running=DashboardLiveRunningDTO(
                count=session_counts.running_count,
                average_duration_ms=session_counts.running_duration // timedelta(milliseconds=1)
                if session_counts.running_duration is not None
                else None,
                phases=[
                    DashboardLivePhaseDTO(phase=phase, count=phase_counts.get(phase.value, 0))
                    for phase in SessionPhaseEnum
                ],
            ),
            today=DashboardLiveTodayDTO(
                started_count=session_counts.started_count,
                ended_count=session_counts.ended_count,
                hourly=[DashboardLiveHourlyDTO(start=hour_start, count=count) for hour_start, count in hourly_counts],
            ),
            last_24_hours=DashboardLiveLast24HoursDTO(
                heartbeat_expired_count=session_counts.heartbeat_expired_count,
                emergency_detected_count=emergency_detected_count,
                judgment_failed_count=judgment_failed_count,
            ),
        ),
        withdrawals=DashboardLiveWithdrawalsDTO(failed_count=failed_withdrawal_count),
    )
