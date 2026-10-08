from datetime import UTC, datetime, time, timedelta

from sqlalchemy import Date, Row, and_, case, cast, exists, func, not_, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.enums import (
    NotificationKindEnum,
    OAuthProviderEnum,
    SessionEndReasonEnum,
    SessionEventKindEnum,
    SessionPhaseEnum,
    SessionStatusEnum,
    SoundJudgmentStatusEnum,
    UserIssueEnum,
    UserLastSessionEnum,
    WithdrawalSessionRangeEnum,
    WithdrawalStatusEnum,
    WithdrawalUsagePeriodEnum,
)
from app.models import (
    Announcement,
    AnnouncementRead,
    Device,
    Feedback,
    I18n,
    Notification,
    Parrot,
    Session,
    SessionEvent,
    SessionSound,
    User,
    UserIdentity,
    UserWithdrawal,
    UserWithdrawalFailure,
)
from app.schemas.base import I18nDTO
from app.schemas.dashboard import (
    AppUpdateDashboardDTO,
    AppUpdateDashboardParams,
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
    FeedbackDashboardAppVersionDTO,
    FeedbackDashboardDTO,
    FeedbackDashboardFeedbackDTO,
    FeedbackDashboardLocaleDTO,
    FeedbackDashboardPlatformDTO,
    NotificationDashboardDailyDTO,
    NotificationDashboardDTO,
    NotificationDashboardKindDTO,
    NotificationDashboardNotificationsDTO,
    UserDashboardAccountsDTO,
    UserDashboardDailyDTO,
    UserDashboardDTO,
    UserDashboardIssueDTO,
    UserDashboardLastSessionDTO,
    UserDashboardParrotsDTO,
    UserDashboardPlatformDTO,
    UserDashboardProviderDTO,
    UserDashboardPushDTO,
    UserDashboardSpeciesDTO,
    UserDashboardUsersDTO,
    UserDashboardWithdrawalsDTO,
    WithdrawalDashboardAccountsDTO,
    WithdrawalDashboardAppVersionDTO,
    WithdrawalDashboardDTO,
    WithdrawalDashboardErrorDTO,
    WithdrawalDashboardParrotsDTO,
    WithdrawalDashboardPlatformDTO,
    WithdrawalDashboardProviderDTO,
    WithdrawalDashboardSessionRangeDTO,
    WithdrawalDashboardUsagePeriodDTO,
    WithdrawalDashboardWithdrawalsDTO,
)
from app.services.devices import LAST_SEEN_DEVICE, MIN_SUPPORTED_APP_UPDATE, VERSION_UNSUPPORTED
from app.services.notifications import NOTIFICATION_PUSH
from app.services.sessions import SESSION_COUNT
from app.services.users import ISSUES, LAST_SESSION, PUSHABLE, SEOUL


async def get_user_counts(
    *, db: AsyncSession, period_start: datetime, period_end: datetime, previous_start: datetime
) -> Row:
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

    return (await db.execute(stmt)).one()


async def get_feedback_counts(
    *, db: AsyncSession, period_start: datetime, period_end: datetime, previous_start: datetime
) -> Row:
    stmt = (
        select(
            func.count().filter(Feedback.created_at >= period_start).label("feedback_count"),
            func.count().filter(Feedback.created_at < period_start).label("previous_feedback_count"),
            func.count(Feedback.user_id.distinct()).filter(Feedback.created_at >= period_start).label("writer_count"),
        )
        .select_from(Feedback)
        .where(Feedback.created_at >= previous_start, Feedback.created_at < period_end)
    )

    return (await db.execute(stmt)).one()


async def get_withdrawal_counts(
    *, db: AsyncSession, period_start: datetime, period_end: datetime, previous_start: datetime
) -> Row:
    stmt = (
        select(
            func.count().filter(UserWithdrawal.created_at >= period_start).label("withdrawal_count"),
            func.count().filter(UserWithdrawal.created_at < period_start).label("previous_withdrawal_count"),
        )
        .select_from(UserWithdrawal)
        .where(UserWithdrawal.created_at >= previous_start, UserWithdrawal.created_at < period_end)
    )

    return (await db.execute(stmt)).one()


async def get_notification_counts(*, db: AsyncSession, period_start: datetime, period_end: datetime) -> list[Row]:
    stmt = (
        select(
            Notification.kind,
            func.count().label("sent_count"),
            func.count(Notification.read_at).label("read_count"),
            func.count(NOTIFICATION_PUSH.c.sent_at).label("push_sent_count"),
        )
        .outerjoin(NOTIFICATION_PUSH, NOTIFICATION_PUSH.c.notification_id == Notification.id)
        .where(
            Notification.sent_at >= period_start,
            Notification.sent_at < period_end,
            Notification.sent_at <= func.now(),
        )
        .group_by(Notification.kind)
    )

    return (await db.execute(stmt)).all()


async def get_daily_counts(
    *, db: AsyncSession, column: InstrumentedAttribute, period_start: datetime, period_end: datetime
) -> dict:
    local_date = cast(func.timezone(SEOUL.key, column), Date)
    stmt = (
        select(local_date, func.count())
        .where(column >= period_start, column < period_end)
        .group_by(local_date)
        .execution_options(include_deleted=True)
    )

    return dict((await db.execute(stmt)).all())


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

    user_counts = await get_user_counts(
        db=db, period_start=period_start, period_end=period_end, previous_start=previous_start
    )

    stmt = (
        select(func.count())
        .select_from(UserWithdrawal)
        .where(UserWithdrawal.created_at >= period_start, UserWithdrawal.created_at < period_end)
    )
    withdrawal_count = await db.scalar(stmt)

    feedback_counts = await get_feedback_counts(
        db=db, period_start=period_start, period_end=period_end, previous_start=previous_start
    )

    daily_counts = {}

    for column in (Session.started_at, User.created_at, UserWithdrawal.created_at):
        daily_counts[column.class_] = await get_daily_counts(
            db=db, column=column, period_start=period_start, period_end=period_end
        )

    notification_counts = await get_notification_counts(db=db, period_start=period_start, period_end=period_end)

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

    stmt = (
        select(func.count())
        .select_from(Device)
        .join(User, User.id == Device.user_id)
        .join(MIN_SUPPORTED_APP_UPDATE, MIN_SUPPORTED_APP_UPDATE.c.platform == Device.platform)
        .where(VERSION_UNSUPPORTED)
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
                DashboardNotificationKindDTO(kind=row.kind, sent_count=row.sent_count, read_count=row.read_count)
                for row in notification_counts
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
            Session.ended_reason == SessionEndReasonEnum.HEARTBEAT_EXPIRED.value,
            Session.ended_at >= since,
        )
        .label("heartbeat_expired_count"),
    ).where(or_(is_running, Session.ended_at >= since))
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
                or_(is_running, Session.ended_at >= since),
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


async def get_user_dashboard(*, db: AsyncSession, query: DashboardParams) -> UserDashboardDTO:
    now = datetime.now(UTC)
    dates = [query.date_from + timedelta(days=offset) for offset in range((query.date_to - query.date_from).days + 1)]
    period_start = datetime.combine(query.date_from, time(0), tzinfo=SEOUL)
    period_end = period_start + timedelta(days=len(dates))
    previous_start = period_start - timedelta(days=len(dates))

    user_counts = await get_user_counts(
        db=db, period_start=period_start, period_end=period_end, previous_start=previous_start
    )

    withdrawal_counts = await get_withdrawal_counts(
        db=db, period_start=period_start, period_end=period_end, previous_start=previous_start
    )

    daily_signup_counts = await get_daily_counts(
        db=db, column=User.created_at, period_start=period_start, period_end=period_end
    )
    daily_withdrawal_counts = await get_daily_counts(
        db=db, column=UserWithdrawal.created_at, period_start=period_start, period_end=period_end
    )

    days = (
        func.generate_series(period_start, period_end - timedelta(days=1), timedelta(days=1))
        .table_valued("day_start")
        .render_derived()
    )
    day_end = days.c.day_start + timedelta(days=1)
    running_user_count = (
        select(func.count(Session.user_id.distinct()))
        .where(Session.started_at < day_end, func.coalesce(Session.ended_at, now) > days.c.day_start)
        .scalar_subquery()
    )
    stmt = select(running_user_count).select_from(days).order_by(days.c.day_start)
    running_user_counts = (await db.scalars(stmt)).all()

    stmt = select(
        select(func.count()).select_from(User).where(User.created_at < period_start).scalar_subquery()
        - select(func.count())
        .select_from(UserWithdrawal)
        .where(UserWithdrawal.created_at < period_start)
        .scalar_subquery()
    ).execution_options(include_deleted=True)
    total_count = await db.scalar(stmt)
    daily = []

    for day, count in zip(dates, running_user_counts, strict=True):
        total_count += daily_signup_counts.get(day, 0) - daily_withdrawal_counts.get(day, 0)

        daily.append(
            UserDashboardDailyDTO(
                date=day,
                total_count=total_count,
                signup_count=daily_signup_counts.get(day, 0),
                withdrawal_count=daily_withdrawal_counts.get(day, 0),
                running_user_count=count,
            )
        )

    stmt = select(LAST_SESSION.label("last_session"), func.count()).select_from(User).group_by("last_session")
    last_session_counts = dict((await db.execute(stmt)).all())

    stmt = (
        select(UserIdentity.provider, func.count())
        .join(User, User.id == UserIdentity.user_id)
        .group_by(UserIdentity.provider)
    )
    provider_counts = dict((await db.execute(stmt)).all())

    stmt = select(func.count().filter(User.is_anonymous), func.count().filter(PUSHABLE)).select_from(User)
    anonymous_count, pushable_count = (await db.execute(stmt)).one()

    stmt = (
        select(func.count().filter(User.is_deleted), *(func.count().filter(ISSUES[issue]) for issue in UserIssueEnum))
        .select_from(User)
        .execution_options(include_deleted=True)
    )
    deleted_count, *issue_counts = (await db.execute(stmt)).one()

    stmt = select(Device.platform, func.count()).join(User, User.id == Device.user_id).group_by(Device.platform)
    platform_counts = (await db.execute(stmt)).all()

    stmt = (
        select(Parrot.species, func.count())
        .join(User, User.id == Parrot.user_id)
        .group_by(Parrot.species)
        .order_by(func.count().desc())
    )
    species_counts = (await db.execute(stmt)).all()

    stmt = select(func.count()).select_from(Parrot).join(User, User.id == Parrot.user_id)
    parrot_count = await db.scalar(stmt)

    return UserDashboardDTO(
        users=UserDashboardUsersDTO(
            total_count=user_counts.total_count,
            signup_count=user_counts.signup_count,
            previous_signup_count=user_counts.previous_signup_count,
            deleted_count=deleted_count,
        ),
        withdrawals=UserDashboardWithdrawalsDTO(
            count=withdrawal_counts.withdrawal_count,
            previous_count=withdrawal_counts.previous_withdrawal_count,
        ),
        daily=daily,
        issues=[
            UserDashboardIssueDTO(issue=issue, count=count)
            for issue, count in zip(UserIssueEnum, issue_counts, strict=True)
        ],
        last_sessions=[
            UserDashboardLastSessionDTO(last_session=last_session, count=last_session_counts.get(last_session.value, 0))
            for last_session in UserLastSessionEnum
        ],
        accounts=UserDashboardAccountsDTO(
            providers=[
                UserDashboardProviderDTO(provider=provider, count=provider_counts.get(provider.value, 0))
                for provider in OAuthProviderEnum
            ],
            anonymous_count=anonymous_count,
        ),
        platforms=[UserDashboardPlatformDTO(platform=platform, count=count) for platform, count in platform_counts],
        push=UserDashboardPushDTO(
            pushable_count=pushable_count,
            unpushable_count=user_counts.total_count - pushable_count,
        ),
        parrots=UserDashboardParrotsDTO(
            total_count=parrot_count,
            species=[UserDashboardSpeciesDTO(species=species, count=count) for species, count in species_counts],
        ),
    )


async def get_feedback_dashboard(*, db: AsyncSession, query: DashboardParams) -> FeedbackDashboardDTO:
    dates = [query.date_from + timedelta(days=offset) for offset in range((query.date_to - query.date_from).days + 1)]
    period_start = datetime.combine(query.date_from, time(0), tzinfo=SEOUL)
    period_end = period_start + timedelta(days=len(dates))
    previous_start = period_start - timedelta(days=len(dates))

    feedback_counts = await get_feedback_counts(
        db=db, period_start=period_start, period_end=period_end, previous_start=previous_start
    )

    daily_counts = await get_daily_counts(
        db=db, column=Feedback.created_at, period_start=period_start, period_end=period_end
    )

    group_counts = {}

    for column in (Feedback.app_version, Device.platform, Device.locale):
        stmt = (
            select(column, func.count())
            .select_from(Feedback)
            .join(Device, Device.id == Feedback.device_id)
            .where(Feedback.created_at >= period_start, Feedback.created_at < period_end)
            .group_by(column)
            .execution_options(include_deleted=True)
        )
        group_counts[column.key] = (await db.execute(stmt)).all()

    return FeedbackDashboardDTO(
        feedback=FeedbackDashboardFeedbackDTO(
            count=feedback_counts.feedback_count,
            previous_count=feedback_counts.previous_feedback_count,
            writer_count=feedback_counts.writer_count,
        ),
        daily=[DashboardDailyCountDTO(date=date, count=daily_counts.get(date, 0)) for date in dates],
        app_versions=[
            FeedbackDashboardAppVersionDTO(app_version=app_version, count=count)
            for app_version, count in group_counts["app_version"]
        ],
        platforms=[
            FeedbackDashboardPlatformDTO(platform=platform, count=count) for platform, count in group_counts["platform"]
        ],
        locales=[FeedbackDashboardLocaleDTO(locale=locale, count=count) for locale, count in group_counts["locale"]],
    )


async def get_withdrawal_dashboard(*, db: AsyncSession, query: DashboardParams) -> WithdrawalDashboardDTO:
    dates = [query.date_from + timedelta(days=offset) for offset in range((query.date_to - query.date_from).days + 1)]
    period_start = datetime.combine(query.date_from, time(0), tzinfo=SEOUL)
    period_end = period_start + timedelta(days=len(dates))
    previous_start = period_start - timedelta(days=len(dates))
    in_period = and_(UserWithdrawal.created_at >= period_start, UserWithdrawal.created_at < period_end)

    withdrawal_counts = await get_withdrawal_counts(
        db=db, period_start=period_start, period_end=period_end, previous_start=previous_start
    )

    user_counts = await get_user_counts(
        db=db, period_start=period_start, period_end=period_end, previous_start=previous_start
    )

    daily_counts = await get_daily_counts(
        db=db, column=UserWithdrawal.created_at, period_start=period_start, period_end=period_end
    )

    has_provider = [
        getattr(UserWithdrawal, f"{provider}_status") != WithdrawalStatusEnum.NOT_REQUIRED.value
        for provider in OAuthProviderEnum
    ]
    has_parrot = exists().where(Parrot.user_id == UserWithdrawal.user_id, Parrot.is_deleted.is_(False))
    stmt = (
        select(
            *(func.count().filter(condition) for condition in has_provider),
            func.count().filter(not_(or_(*has_provider))),
            func.count().filter(has_parrot),
        )
        .select_from(UserWithdrawal)
        .where(in_period)
    )
    *provider_counts, anonymous_count, registered_parrot_count = (await db.execute(stmt)).one()

    usage_days = cast(func.timezone(SEOUL.key, UserWithdrawal.created_at), Date) - cast(
        func.timezone(SEOUL.key, User.created_at), Date
    )
    ranges = {
        "usage_period": case(
            (usage_days <= 0, WithdrawalUsagePeriodEnum.SAME_DAY.value),
            (usage_days <= 7, WithdrawalUsagePeriodEnum.WITHIN_7_DAYS.value),
            (usage_days <= 30, WithdrawalUsagePeriodEnum.WITHIN_30_DAYS.value),
            else_=WithdrawalUsagePeriodEnum.OVER_30_DAYS.value,
        ),
        "session_range": case(
            (SESSION_COUNT == 0, WithdrawalSessionRangeEnum.NONE.value),
            (SESSION_COUNT <= 4, WithdrawalSessionRangeEnum.ONE_TO_FOUR.value),
            else_=WithdrawalSessionRangeEnum.FIVE_OR_MORE.value,
        ),
    }
    group_counts = {}

    for name, column in ranges.items():
        stmt = (
            select(column.label(name), func.count())
            .select_from(UserWithdrawal)
            .join(User, User.id == UserWithdrawal.user_id)
            .where(in_period)
            .group_by(name)
            .execution_options(include_deleted=True)
        )
        group_counts[name] = dict((await db.execute(stmt)).all())

    for column in (LAST_SEEN_DEVICE.c.platform, LAST_SEEN_DEVICE.c.app_version):
        stmt = (
            select(column, func.count())
            .select_from(UserWithdrawal)
            .join(User, User.id == UserWithdrawal.user_id)
            .join(LAST_SEEN_DEVICE, true())
            .where(in_period)
            .group_by(column)
            .execution_options(include_deleted=True)
        )
        group_counts[column.key] = (await db.execute(stmt)).all()

    stmt = (
        select(UserWithdrawalFailure.error_code, func.count())
        .where(UserWithdrawalFailure.created_at >= period_start, UserWithdrawalFailure.created_at < period_end)
        .group_by(UserWithdrawalFailure.error_code)
        .order_by(func.count().desc(), UserWithdrawalFailure.error_code)
    )
    error_counts = (await db.execute(stmt)).all()

    return WithdrawalDashboardDTO(
        withdrawals=WithdrawalDashboardWithdrawalsDTO(
            count=withdrawal_counts.withdrawal_count,
            previous_count=withdrawal_counts.previous_withdrawal_count,
        ),
        signup_count=user_counts.signup_count,
        daily=[DashboardDailyCountDTO(date=date, count=daily_counts.get(date, 0)) for date in dates],
        accounts=WithdrawalDashboardAccountsDTO(
            providers=[
                WithdrawalDashboardProviderDTO(provider=provider, count=count)
                for provider, count in zip(OAuthProviderEnum, provider_counts, strict=True)
            ],
            anonymous_count=anonymous_count,
        ),
        platforms=[
            WithdrawalDashboardPlatformDTO(platform=platform, count=count)
            for platform, count in group_counts["platform"]
        ],
        app_versions=[
            WithdrawalDashboardAppVersionDTO(app_version=app_version, count=count)
            for app_version, count in group_counts["app_version"]
        ],
        usage_periods=[
            WithdrawalDashboardUsagePeriodDTO(
                usage_period=usage_period, count=group_counts["usage_period"].get(usage_period.value, 0)
            )
            for usage_period in WithdrawalUsagePeriodEnum
        ],
        session_ranges=[
            WithdrawalDashboardSessionRangeDTO(
                session_range=session_range, count=group_counts["session_range"].get(session_range.value, 0)
            )
            for session_range in WithdrawalSessionRangeEnum
        ],
        parrots=WithdrawalDashboardParrotsDTO(
            registered_count=registered_parrot_count,
            unregistered_count=withdrawal_counts.withdrawal_count - registered_parrot_count,
        ),
        errors=[WithdrawalDashboardErrorDTO(error_code=error_code, count=count) for error_code, count in error_counts],
    )


async def get_notification_dashboard(*, db: AsyncSession, query: DashboardParams) -> NotificationDashboardDTO:
    dates = [query.date_from + timedelta(days=offset) for offset in range((query.date_to - query.date_from).days + 1)]
    period_start = datetime.combine(query.date_from, time(0), tzinfo=SEOUL)
    period_end = period_start + timedelta(days=len(dates))
    previous_start = period_start - timedelta(days=len(dates))

    notification_counts = await get_notification_counts(db=db, period_start=period_start, period_end=period_end)
    previous_counts = await get_notification_counts(db=db, period_start=previous_start, period_end=period_start)

    local_date = cast(func.timezone(SEOUL.key, Notification.sent_at), Date)
    stmt = (
        select(local_date, Notification.kind, func.count())
        .where(
            Notification.sent_at >= period_start,
            Notification.sent_at < period_end,
            Notification.sent_at <= func.now(),
        )
        .group_by(local_date, Notification.kind)
    )
    daily_counts = {(date, kind): count for date, kind, count in (await db.execute(stmt)).all()}

    return NotificationDashboardDTO(
        notifications=NotificationDashboardNotificationsDTO(
            count=sum(row.sent_count for row in notification_counts),
            previous_count=sum(row.sent_count for row in previous_counts),
        ),
        kinds=[
            NotificationDashboardKindDTO(
                kind=row.kind,
                sent_count=row.sent_count,
                read_count=row.read_count,
                push_sent_count=row.push_sent_count,
            )
            for row in notification_counts
        ],
        daily=[
            NotificationDashboardDailyDTO(
                date=date,
                report_count=daily_counts.get((date, NotificationKindEnum.REPORT.value), 0),
                announcement_count=daily_counts.get((date, NotificationKindEnum.ANNOUNCEMENT.value), 0),
                marketing_count=daily_counts.get((date, NotificationKindEnum.MARKETING.value), 0),
                urgent_count=daily_counts.get((date, NotificationKindEnum.URGENT.value), 0),
            )
            for date in dates
        ],
    )


async def get_app_update_dashboard(*, db: AsyncSession, query: AppUpdateDashboardParams) -> AppUpdateDashboardDTO:
    stmt = (
        select(Device.app_version, func.count())
        .join(User, User.id == Device.user_id)
        .where(Device.platform == query.platform.value)
        .group_by(Device.app_version)
    )
    device_versions = (await db.execute(stmt)).all()

    return AppUpdateDashboardDTO(
        versions=[
            DashboardDeviceVersionDTO(app_version=app_version, count=count) for app_version, count in device_versions
        ]
    )
