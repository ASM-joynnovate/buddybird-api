from datetime import UTC, datetime, time, timedelta
from secrets import SystemRandom
from uuid import UUID, uuid7

from pydantic.experimental.missing_sentinel import MISSING
from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import AdImageKindEnum, AdKindEnum, AdStatusEnum, FeedItemKindEnum, FileStatusEnum, LocaleEnum
from app.errors import (
    AdOrderMismatchError,
    AdSaveUnavailableError,
    DuplicateAdImageError,
    FileSizeExceededError,
    InvalidAdCreativeError,
    InvalidAdI18nError,
    InvalidAdPeriodError,
    InvalidProfilePhotoError,
    ResourceNotFoundError,
)
from app.file import build_public_file_dto, ensure_uploaded_photo
from app.models import Ad, AdCountry, AdEvent, AdHourlyStat, Device, File, I18n, User
from app.s3 import S3StorageClient
from app.schemas.ads import (
    AddAdEventsRequest,
    AdEventCountDTO,
    AdImageUploadRequest,
    AdListParams,
    AdStatDTO,
    AdTotalStatDTO,
    BackofficeAdDTO,
    BackofficeAdFileDTO,
    BackofficeAdListParams,
    BackofficeAdStatsParams,
    CreateAdRequest,
    FeedAdDTO,
    HomeBannerAdDTO,
    UpdateAdRequest,
)
from app.schemas.base import I18nDTO, ReorderRequest, UploadDTO
from app.utils import MAX_PHOTO_BYTES, PHOTO_TYPES, SEOUL


def check_creative(ad: Ad) -> None:
    feed_fields = (ad.advertiser_photo_file, ad.body_i18n, ad.button_text_i18n, ad.button_color, ad.button_text_color)
    banner_invalid = ad.kind == AdKindEnum.HOME_BANNER.value and any(field is not None for field in feed_fields)
    feed_invalid = ad.kind == AdKindEnum.FEED.value and any(field is None for field in feed_fields)

    if banner_invalid or feed_invalid:
        raise InvalidAdCreativeError


def select_active_ads(*, user: User, kind: AdKindEnum, now: datetime) -> Select:
    target_user = or_(
        ~exists().where(AdCountry.ad_id == Ad.id).correlate(Ad),
        exists().where(AdCountry.ad_id == Ad.id, AdCountry.country == User.country).correlate(Ad, User),
    )

    return select(Ad).where(
        Ad.kind == kind.value,
        Ad.is_enabled.is_(True),
        Ad.starts_at <= now,
        or_(Ad.ends_at.is_(None), Ad.ends_at > now),
        exists().where(User.id == user.id, target_user),
    )


def build_home_banner_ad_dto(ad: Ad, locale: LocaleEnum, storage: S3StorageClient) -> HomeBannerAdDTO:
    return HomeBannerAdDTO(
        id=ad.id,
        serve_id=uuid7(),
        is_ad=ad.is_ad,
        advertiser_name=ad.advertiser_name_i18n.get_text(locale),
        link_url=ad.link_url_i18n.get_text(locale),
        image_file=build_public_file_dto(storage=storage, file=ad.image_file),
    )


def build_feed_ad_dto(ad: Ad, locale: LocaleEnum, storage: S3StorageClient) -> FeedAdDTO:
    return FeedAdDTO(
        id=ad.id,
        kind=FeedItemKindEnum.AD,
        serve_id=uuid7(),
        is_ad=ad.is_ad,
        advertiser_name=ad.advertiser_name_i18n.get_text(locale),
        advertiser_description=ad.advertiser_description_i18n.get_text(locale)
        if ad.advertiser_description_i18n is not None
        else None,
        advertiser_photo_file=build_public_file_dto(storage=storage, file=ad.advertiser_photo_file),
        link_url=ad.link_url_i18n.get_text(locale),
        body=ad.body_i18n.get_text(locale),
        image_file=build_public_file_dto(storage=storage, file=ad.image_file),
        button_text=ad.button_text_i18n.get_text(locale),
        button_color=ad.button_color,
        button_text_color=ad.button_text_color,
    )


def build_backoffice_ad_dto(ad: Ad, storage: S3StorageClient, event_counts: list[AdEventCountDTO]) -> BackofficeAdDTO:
    now = datetime.now(UTC)

    if not ad.is_enabled:
        status = AdStatusEnum.DISABLED
    elif ad.starts_at > now:
        status = AdStatusEnum.SCHEDULED
    elif ad.ends_at is not None and ad.ends_at <= now:
        status = AdStatusEnum.ENDED
    else:
        status = AdStatusEnum.ACTIVE

    return BackofficeAdDTO(
        id=ad.id,
        kind=ad.kind,
        status=status,
        is_ad=ad.is_ad,
        is_enabled=ad.is_enabled,
        starts_at=ad.starts_at,
        ends_at=ad.ends_at,
        weight=ad.weight,
        display_order=ad.display_order,
        countries=[ad_country.country for ad_country in ad.countries],
        advertiser_name=I18nDTO.model_validate(ad.advertiser_name_i18n, from_attributes=True),
        advertiser_description=I18nDTO.model_validate(ad.advertiser_description_i18n, from_attributes=True)
        if ad.advertiser_description_i18n is not None
        else None,
        advertiser_photo_file=BackofficeAdFileDTO(
            file_id=ad.advertiser_photo_file_id,
            url=storage.generate_presigned_url(path=ad.advertiser_photo_file.object_key),
        )
        if ad.advertiser_photo_file is not None
        else None,
        link_url=I18nDTO.model_validate(ad.link_url_i18n, from_attributes=True),
        image_file=BackofficeAdFileDTO(
            file_id=ad.image_file_id, url=storage.generate_presigned_url(path=ad.image_file.object_key)
        ),
        body=I18nDTO.model_validate(ad.body_i18n, from_attributes=True) if ad.body_i18n is not None else None,
        button_text=I18nDTO.model_validate(ad.button_text_i18n, from_attributes=True)
        if ad.button_text_i18n is not None
        else None,
        button_color=ad.button_color,
        button_text_color=ad.button_text_color,
        event_counts=event_counts,
    )


async def get_event_counts(*, db: AsyncSession, ad_ids: list[UUID]) -> dict[UUID, list[AdEventCountDTO]]:
    stmt = (
        select(AdHourlyStat.ad_id, AdHourlyStat.kind, func.sum(AdHourlyStat.count))
        .where(AdHourlyStat.ad_id.in_(ad_ids))
        .group_by(AdHourlyStat.ad_id, AdHourlyStat.kind)
        .order_by(AdHourlyStat.kind)
    )
    rows = (await db.execute(stmt)).all()
    counts = {ad_id: [] for ad_id in ad_ids}

    for ad_id, kind, count in rows:
        counts[ad_id].append(AdEventCountDTO(kind=kind, count=count))

    return counts


async def get_ad_file(*, db: AsyncSession, storage: S3StorageClient, file_id: UUID, kind: AdImageKindEnum) -> File:
    stmt = select(File).where(File.id == file_id, File.file_path == f"ad/{kind.value}/{file_id}")
    file = await db.scalar(stmt)

    if file is None:
        raise ResourceNotFoundError

    stmt = select(
        exists().where(or_(Ad.image_file_id == file_id, Ad.advertiser_photo_file_id == file_id))
    ).execution_options(include_deleted=True)

    if await db.scalar(stmt):
        raise DuplicateAdImageError

    await ensure_uploaded_photo(storage=storage, file=file)

    return file


async def get_list(
    *, db: AsyncSession, user: User, locale: LocaleEnum, storage: S3StorageClient, query: AdListParams
) -> list[HomeBannerAdDTO]:
    stmt = select_active_ads(user=user, kind=query.kind, now=datetime.now(UTC)).order_by(Ad.display_order)
    ads = (await db.scalars(stmt)).all()

    return [build_home_banner_ad_dto(ad, locale, storage) for ad in ads]


async def pick_feed_ads(
    *, db: AsyncSession, user: User, locale: LocaleEnum, storage: S3StorageClient, count: int
) -> list[FeedAdDTO]:
    stmt = select_active_ads(user=user, kind=AdKindEnum.FEED, now=datetime.now(UTC))
    candidates = list((await db.scalars(stmt)).all())
    random = SystemRandom()
    picked = []

    while candidates and len(picked) < count:
        ad = random.choices(candidates, weights=[candidate.weight for candidate in candidates])[0]

        candidates.remove(ad)
        picked.append(build_feed_ad_dto(ad, locale, storage))

    return picked


@transactional(unavailable_error=AdSaveUnavailableError)
async def add_events(
    *, db: AsyncSession, user: User, device: Device, locale: LocaleEnum, data: AddAdEventsRequest
) -> None:
    stmt = (
        insert(AdEvent)
        .values(
            [
                {
                    "ad_id": event.ad_id,
                    "user_id": user.id,
                    "device_id": device.id,
                    "serve_id": event.serve_id,
                    "kind": event.kind.value,
                    "position": event.position,
                    "click_target": event.click_target.value if event.click_target is not None else None,
                    "visible_duration_ms": event.visible_duration_ms,
                    "occurred_at": event.occurred_at,
                    "country": user.country,
                    "locale": locale.value,
                    "platform": device.platform,
                    "app_version": device.app_version,
                    "os_version": device.os_version,
                }
                for event in data.events
            ]
        )
        .on_conflict_do_nothing()
        .returning(AdEvent.ad_id, AdEvent.kind, AdEvent.occurred_at)
    )
    rows = (await db.execute(stmt)).all()
    counts = {}

    for ad_id, kind, occurred_at in rows:
        occurred_hour = occurred_at.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        counts[ad_id, occurred_hour, kind] = counts.get((ad_id, occurred_hour, kind), 0) + 1

    if not counts:
        return

    stmt = insert(AdHourlyStat).values(
        [
            {"ad_id": ad_id, "occurred_hour": occurred_hour, "kind": kind, "count": count}
            for (ad_id, occurred_hour, kind), count in counts.items()
        ]
    )

    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[AdHourlyStat.ad_id, AdHourlyStat.occurred_hour, AdHourlyStat.kind],
            set_={"count": AdHourlyStat.count + stmt.excluded.count, "updated_at": func.now()},
        )
    )


async def get_backoffice_list(
    *, db: AsyncSession, storage: S3StorageClient, query: BackofficeAdListParams
) -> tuple[list[BackofficeAdDTO], int]:
    now = datetime.now(UTC)
    stmt = select(Ad)

    if query.kind is not None:
        stmt = stmt.where(Ad.kind == query.kind.value)

    if query.is_ad is not None:
        stmt = stmt.where(Ad.is_ad.is_(query.is_ad))

    if query.country is not None:
        stmt = stmt.where(
            or_(
                ~exists().where(AdCountry.ad_id == Ad.id),
                exists().where(AdCountry.ad_id == Ad.id, AdCountry.country == query.country),
            )
        )

    if query.status is not None:
        stmt = stmt.where(
            {
                AdStatusEnum.SCHEDULED: and_(Ad.is_enabled.is_(True), Ad.starts_at > now),
                AdStatusEnum.ACTIVE: and_(
                    Ad.is_enabled.is_(True), Ad.starts_at <= now, or_(Ad.ends_at.is_(None), Ad.ends_at > now)
                ),
                AdStatusEnum.ENDED: and_(Ad.is_enabled.is_(True), Ad.ends_at <= now),
                AdStatusEnum.DISABLED: Ad.is_enabled.is_(False),
            }[query.status]
        )

    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    ads = (
        await db.scalars(
            stmt.order_by(Ad.starts_at.desc()).offset((query.page - 1) * query.count_by_page).limit(query.count_by_page)
        )
    ).all()

    counts = await get_event_counts(db=db, ad_ids=[ad.id for ad in ads])

    return [build_backoffice_ad_dto(ad, storage, counts[ad.id]) for ad in ads], total


async def get_detail(*, db: AsyncSession, storage: S3StorageClient, ad: Ad) -> BackofficeAdDTO:
    counts = await get_event_counts(db=db, ad_ids=[ad.id])

    return build_backoffice_ad_dto(ad, storage, counts[ad.id])


@transactional(unavailable_error=AdSaveUnavailableError)
async def create(*, db: AsyncSession, storage: S3StorageClient, data: CreateAdRequest) -> BackofficeAdDTO:
    image_file = await get_ad_file(
        db=db, storage=storage, file_id=data.image_file_id, kind=AdImageKindEnum(data.kind.value)
    )
    advertiser_photo_file = None

    if data.advertiser_photo_file_id is not None:
        advertiser_photo_file = await get_ad_file(
            db=db, storage=storage, file_id=data.advertiser_photo_file_id, kind=AdImageKindEnum.ADVERTISER
        )

    display_order = None

    if data.kind == AdKindEnum.HOME_BANNER:
        stmt = select(func.coalesce(func.max(Ad.display_order) + 1, 0)).where(Ad.kind == AdKindEnum.HOME_BANNER.value)
        display_order = await db.scalar(stmt)

    ad = Ad(
        kind=data.kind.value,
        is_ad=data.is_ad,
        is_enabled=data.is_enabled,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        weight=data.weight,
        display_order=display_order,
        advertiser_name_i18n=I18n(**data.advertiser_name.model_dump()),
        advertiser_description_i18n=I18n(**data.advertiser_description.model_dump())
        if data.advertiser_description is not None
        else None,
        advertiser_photo_file=advertiser_photo_file,
        link_url_i18n=I18n(**data.link_url.model_dump()),
        image_file=image_file,
        body_i18n=I18n(**data.body.model_dump()) if data.body is not None else None,
        button_text_i18n=I18n(**data.button_text.model_dump()) if data.button_text is not None else None,
        button_color=data.button_color,
        button_text_color=data.button_text_color,
        is_deleted=False,
        countries=[AdCountry(country=country) for country in sorted(data.countries)],
    )

    check_creative(ad)

    db.add(ad)
    await db.flush()

    return build_backoffice_ad_dto(ad, storage, [])


@transactional(unavailable_error=AdSaveUnavailableError)
async def update(*, db: AsyncSession, storage: S3StorageClient, ad: Ad, data: UpdateAdRequest) -> BackofficeAdDTO:
    for name in ("advertiser_name", "link_url"):
        value = getattr(data, name)

        if value is not MISSING:
            for field, text in value.model_dump(exclude_unset=True).items():
                setattr(getattr(ad, f"{name}_i18n"), field, text)

    for name in ("advertiser_description", "body", "button_text"):
        value = getattr(data, name)
        current = getattr(ad, f"{name}_i18n")

        if value is None:
            setattr(ad, f"{name}_i18n", None)
        elif value is not MISSING and current is not None:
            for field, text in value.model_dump(exclude_unset=True).items():
                setattr(current, field, text)
        elif value is not MISSING:
            if value.en_us is MISSING:
                raise InvalidAdI18nError

            setattr(ad, f"{name}_i18n", I18n(**value.model_dump(exclude_unset=True)))

    for name, value in data.model_dump(
        exclude_unset=True,
        exclude={
            "advertiser_name",
            "link_url",
            "advertiser_description",
            "body",
            "button_text",
            "countries",
            "image_file_id",
            "advertiser_photo_file_id",
        },
    ).items():
        setattr(ad, name, value)

    if ad.ends_at is not None and ad.ends_at <= ad.starts_at:
        raise InvalidAdPeriodError

    if data.countries is not MISSING:
        ad_countries = {ad_country.country: ad_country for ad_country in ad.countries}

        ad.countries = [ad_countries.get(country) or AdCountry(country=country) for country in sorted(data.countries)]

    if data.image_file_id is not MISSING and data.image_file_id != ad.image_file_id:
        image_file = await get_ad_file(
            db=db, storage=storage, file_id=data.image_file_id, kind=AdImageKindEnum(ad.kind)
        )

        ad.image_file.is_deleted = True
        ad.image_file = image_file

    if data.advertiser_photo_file_id is not MISSING and data.advertiser_photo_file_id != ad.advertiser_photo_file_id:
        advertiser_photo_file = None

        if data.advertiser_photo_file_id is not None:
            advertiser_photo_file = await get_ad_file(
                db=db, storage=storage, file_id=data.advertiser_photo_file_id, kind=AdImageKindEnum.ADVERTISER
            )

        if ad.advertiser_photo_file is not None:
            ad.advertiser_photo_file.is_deleted = True

        ad.advertiser_photo_file = advertiser_photo_file

    check_creative(ad)

    await db.flush()

    return await get_detail(db=db, storage=storage, ad=ad)


@transactional(unavailable_error=AdSaveUnavailableError)
async def delete(*, db: AsyncSession, ad: Ad) -> None:
    ad.is_deleted = True
    ad.image_file.is_deleted = True

    if ad.advertiser_photo_file is not None:
        ad.advertiser_photo_file.is_deleted = True

    await db.flush()


@transactional(unavailable_error=AdSaveUnavailableError)
async def reorder(*, db: AsyncSession, storage: S3StorageClient, data: ReorderRequest) -> list[BackofficeAdDTO]:
    now = datetime.now(UTC)
    stmt = select(Ad).where(Ad.kind == AdKindEnum.HOME_BANNER.value, or_(Ad.ends_at.is_(None), Ad.ends_at > now))
    banners = {ad.id: ad for ad in (await db.scalars(stmt)).all()}

    if sorted(data.ids) != sorted(banners):
        raise AdOrderMismatchError

    for display_order, ad_id in enumerate(data.ids):
        banners[ad_id].display_order = display_order

    await db.flush()

    counts = await get_event_counts(db=db, ad_ids=data.ids)

    return [build_backoffice_ad_dto(banners[ad_id], storage, counts[ad_id]) for ad_id in data.ids]


@transactional(unavailable_error=AdSaveUnavailableError)
async def add_image(*, db: AsyncSession, storage: S3StorageClient, data: AdImageUploadRequest) -> UploadDTO:
    if data.content_type not in PHOTO_TYPES:
        raise InvalidProfilePhotoError

    if data.file_size > MAX_PHOTO_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()

    image_file = File(
        id=file_id,
        file_name="image.jpg",
        file_path=f"ad/{data.kind.value}/{file_id}",
        file_size=data.file_size,
        file_type="image/jpeg",
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(image_file)

    await db.flush()

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=f"upload/{image_file.object_key}",
        content_type=data.content_type,
        file_size=data.file_size,
    )


def build_stats_stmt(query: BackofficeAdStatsParams) -> Select:
    period_start = datetime.combine(query.date_from, time(0), tzinfo=SEOUL)
    period_end = datetime.combine(query.date_to + timedelta(days=1), time(0), tzinfo=SEOUL)
    started_at = func.timezone(
        SEOUL.key,
        func.date_trunc(query.interval.value, func.timezone(SEOUL.key, AdHourlyStat.occurred_hour)),
    )

    return (
        select(started_at, AdHourlyStat.kind, func.sum(AdHourlyStat.count))
        .where(
            AdHourlyStat.occurred_hour >= period_start,
            AdHourlyStat.occurred_hour < period_end,
        )
        .group_by(started_at, AdHourlyStat.kind)
        .order_by(started_at, AdHourlyStat.kind)
    )


async def get_stats(*, db: AsyncSession, ad: Ad, query: BackofficeAdStatsParams) -> list[AdStatDTO]:
    stmt = build_stats_stmt(query).where(AdHourlyStat.ad_id == ad.id)
    rows = (await db.execute(stmt)).all()

    return [AdStatDTO(started_at=started_at, kind=kind, count=count) for started_at, kind, count in rows]


async def get_total_stats(*, db: AsyncSession, query: BackofficeAdStatsParams) -> list[AdTotalStatDTO]:
    stmt = (
        build_stats_stmt(query)
        .add_columns(Ad.kind)
        .join(Ad, Ad.id == AdHourlyStat.ad_id)
        .where(Ad.is_ad.is_(True))
        .group_by(Ad.kind)
        .order_by(Ad.kind)
        .execution_options(include_deleted=True)
    )
    rows = (await db.execute(stmt)).all()

    return [
        AdTotalStatDTO(started_at=started_at, kind=kind, count=count, ad_kind=ad_kind)
        for started_at, kind, count, ad_kind in rows
    ]
