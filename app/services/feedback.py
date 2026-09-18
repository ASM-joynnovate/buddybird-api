from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import FeedbackSaveUnavailableError
from app.models import Device, Feedback, User
from app.schemas.base import PageParams
from app.schemas.feedback import CreateFeedbackRequest, FeedbackDTO


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


async def get_list(*, db: AsyncSession, query: PageParams) -> tuple[list[FeedbackDTO], int]:
    stmt = select(Feedback)
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    feedbacks = (
        await db.scalars(
            stmt.order_by(Feedback.created_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return [build_feedback_dto(feedback) for feedback in feedbacks], total
