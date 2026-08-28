from uuid import UUID

from app.audio_capture.application.dto.label import (
    CreateLabelCategoryDTO,
    CreateLabelOptionDTO,
    UpdateLabelCategoryDTO,
    UpdateLabelOptionDTO,
)
from app.audio_capture.domain.command.label import (
    CreateLabelCategoryCommand,
    CreateLabelOptionCommand,
    UpdateLabelCategoryCommand,
    UpdateLabelOptionCommand,
)
from app.audio_capture.domain.entities.label import LabelCategory, LabelOption
from app.audio_capture.domain.interfaces.repositories import ILabelCategoryRepo, ILabelOptionRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class CreateLabelCategoryUseCase:
    def __init__(self, *, label_category_repo: ILabelCategoryRepo):
        self._label_category_repo = label_category_repo

    @Transactional()
    async def execute(self, *, data: CreateLabelCategoryDTO) -> None:
        category = LabelCategory.create(
            command=CreateLabelCategoryCommand(name=data.name, display_order=data.display_order, target=data.target)
        )
        await self._label_category_repo.save(label_category=category)


class UpdateLabelCategoryUseCase:
    def __init__(self, *, label_category_repo: ILabelCategoryRepo):
        self._label_category_repo = label_category_repo

    @Transactional()
    async def execute(self, *, label_category_id: UUID, data: UpdateLabelCategoryDTO) -> None:
        category = await self._label_category_repo.get_by_id(label_category_id=label_category_id)
        if category is None:
            raise ResourceNotFoundError
        category.update(command=UpdateLabelCategoryCommand(name=data.name, display_order=data.display_order))


class DeleteLabelCategoryUseCase:
    def __init__(self, *, label_category_repo: ILabelCategoryRepo):
        self._label_category_repo = label_category_repo

    @Transactional()
    async def execute(self, *, label_category_id: UUID) -> None:
        category = await self._label_category_repo.get_by_id(label_category_id=label_category_id)
        if category is None:
            raise ResourceNotFoundError
        for option in category.options:
            option.delete()
        category.delete()


class CreateLabelOptionUseCase:
    def __init__(self, *, label_category_repo: ILabelCategoryRepo, label_option_repo: ILabelOptionRepo):
        self._label_category_repo = label_category_repo
        self._label_option_repo = label_option_repo

    @Transactional()
    async def execute(self, *, label_category_id: UUID, data: CreateLabelOptionDTO) -> None:
        category = await self._label_category_repo.get_by_id(label_category_id=label_category_id)
        if category is None:
            raise ResourceNotFoundError
        option = LabelOption.create(
            command=CreateLabelOptionCommand(
                category_id=label_category_id, name=data.name, display_order=data.display_order
            )
        )
        await self._label_option_repo.save(label_option=option)


class UpdateLabelOptionUseCase:
    def __init__(self, *, label_option_repo: ILabelOptionRepo):
        self._label_option_repo = label_option_repo

    @Transactional()
    async def execute(self, *, label_option_id: UUID, data: UpdateLabelOptionDTO) -> None:
        option = await self._label_option_repo.get_by_id(label_option_id=label_option_id)
        if option is None:
            raise ResourceNotFoundError
        option.update(command=UpdateLabelOptionCommand(name=data.name, display_order=data.display_order))


class DeleteLabelOptionUseCase:
    def __init__(self, *, label_option_repo: ILabelOptionRepo):
        self._label_option_repo = label_option_repo

    @Transactional()
    async def execute(self, *, label_option_id: UUID) -> None:
        option = await self._label_option_repo.get_by_id(label_option_id=label_option_id)
        if option is None:
            raise ResourceNotFoundError
        option.delete()
