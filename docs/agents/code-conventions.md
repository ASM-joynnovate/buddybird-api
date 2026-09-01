# 코드 컨벤션

## 파일 배치

### 디렉터리

```text
app/
└── <domain>/
    ├── application/
    │   ├── dto/
    │   ├── errors/
    │   └── use_cases/
    │       ├── command/
    │       └── query/
    ├── domain/
    │   ├── commands/
    │   ├── entities/
    │   ├── errors/
    │   ├── interfaces/
    │   │   ├── repositories/
    │   │   └── services/
    │   └── value_objects/
    ├── infra/
    │   ├── persistence/
    │   │   └── sqlalchemy/
    │   └── services/
    ├── presentation/
    │   └── rest/
    │       └── v1/
    │           ├── errors/
    │           ├── request/
    │           └── response/
    └── container.py
```

### 파일 이름

Use case 구현은 기능별 파일 하나로 작성합니다.

같은 리소스의 Repository Interface와 SQLAlchemy Repository 구현은 각각 파일 하나로 작성합니다.

Use case 파일 이름은 `<동사>_<명사>.py` 형식으로 작성합니다.

Mapping과 Error 파일 이름은 리소스의 Snake Case 이름으로 작성합니다.

```text
application/use_cases/command/create_item.py
application/use_cases/query/get_item.py
domain/interfaces/repositories/item.py
infra/persistence/sqlalchemy/item.py
domain/errors/item.py
application/errors/item.py
presentation/rest/v1/errors/item.py
```

## Import

### `__init__.py`

#### 빈 파일

레이어 루트와 `entities`, `use_cases`의 `__init__.py`는 빈 파일로 유지합니다.

#### Re-Export

나머지 `__init__.py`는 모듈의 모든 공개 이름을 상대 Import로 Re-Export하고 `__all__`에 나열합니다.

```python
from .item import CreateItemDTO, GetItemDTO

__all__ = [
    "CreateItemDTO",
    "GetItemDTO",
]
```

### 경로

#### 일반 모듈

```python
from app.example.application.dto import CreateItemDTO
from app.example.application.use_cases.command.create_item import CreateItemUseCase
from app.example.domain.commands import CreateItemCommand
from app.example.domain.entities.item import Item
from app.example.domain.interfaces.repositories import IItemRepo
```

#### Transaction Helper

```python
from core.db import Transactional, on_rollback
```

#### 상대 Import

상대 Import는 `__init__.py`에서만 사용합니다.

## Command

```python
from dataclasses import dataclass

from core.common.sentinel import MISSING


@dataclass(frozen=True)
class UpdateItemCommand:
    name: str | MISSING
    display_order: int | MISSING
```

## Entity

```python
from dataclasses import dataclass, field
from uuid import UUID, uuid7

from app.example.domain.commands import CreateItemCommand, UpdateItemCommand
from core.common.sentinel import MISSING


@dataclass(eq=False)
class Entity:
    id: UUID = field(kw_only=True, default_factory=uuid7)


@dataclass(eq=False)
class Item(Entity):
    name: str
    description: str | None
    display_order: int
    is_deleted: bool

    @classmethod
    def create(cls, *, command: CreateItemCommand) -> Item:
        return cls(
            id=uuid7(),
            name=command.name,
            description=None,
            display_order=0,
            is_deleted=False,
        )

    def update(self, *, command: UpdateItemCommand) -> None:
        if command.name is not MISSING:
            self.name = command.name
        if command.display_order is not MISSING:
            self.display_order = command.display_order

    def delete(self) -> None:
        self.is_deleted = True
```

### 시간 필드

`created_at`과 `updated_at`은 SQLAlchemy `BaseTable` 컬럼으로만 선언합니다.

## Enum

```python
from enum import StrEnum


class ItemStatusEnum(StrEnum):
    ACTIVE = "AC"
    INACTIVE = "IN"
```

## 상수

### 배치

Domain 상수는 `app/<domain>/domain/constants.py`에 배치합니다.

### 선언

```python
MAX_FILE_SIZE = "10MB"
ALLOWED_MIME_TYPES = ["application/octet-stream", "text/plain"]
```

## Interface

```python
from abc import ABC, abstractmethod


class IItemRepo(ABC):
    @abstractmethod
    async def get_by_id(self, *, item_id: UUID) -> Item | None: ...

    @abstractmethod
    async def save(self, *, item: Item) -> None: ...
```

구현 클래스의 메서드 순서는 Interface와 같게 작성합니다.

## Use case

### Command

```python
class CreateItemUseCase:
    def __init__(
        self,
        *,
        item_repo: IItemRepo,
    ):
        self._item_repo = item_repo

    @Transactional()
    async def execute(self, *, data: CreateItemDTO) -> None:
        item = Item.create(command=CreateItemCommand(name=data.name))

        await self._item_repo.save(item=item)
```

### Query

```python
class GetItemUseCase:
    def __init__(
        self,
        *,
        item_repo: IItemRepo,
    ):
        self._item_repo = item_repo

    async def execute(self, *, item_id: UUID) -> GetItemDTO:
        item = await self._item_repo.get_by_id(item_id=item_id)
        if item is None:
            raise ItemNotFoundError

        return GetItemDTO(
            id=item.id,
            description=item.description,
        )
```

### Collection 검증

```python
items = await self._item_repo.get_by_ids(item_ids=data.item_ids)
if len(items) != len(data.item_ids):
    raise ItemNotFoundError
```

### 반환 타입


| Use case     | 반환 타입     |
| ------------ | --------- |
| Entity Query | DTO       |
| Scalar Query | Scalar 타입 |
| Binary Query | `bytes`   |


## DTO

```python
from typing import ClassVar

from pydantic import Field

from core.common import CustomBaseModel


class CreateItemDTO(CustomBaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class GetItemDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"description"}

    id: UUID = Field(...)
    description: str | None = Field(None)
```

## Request

### 모델

```python
from typing import ClassVar

from pydantic import Field, field_validator

from core.common.request import BaseRequest, PageParams
from core.common.sentinel import MISSING


class CreateOptionRequest(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, examples=["example"])


class UpdateItemRequest(BaseRequest):
    null_fields: ClassVar[set] = {"parent_id"}
    empty_str_fields: ClassVar[set] = {"memo"}

    name: str | MISSING = Field(
        MISSING,
        min_length=1,
        max_length=100,
        examples=["example"],
    )
    parent_id: UUID | None | MISSING = Field(
        MISSING,
        examples=["01900000-0000-7000-8000-000000000000", None],
    )
    memo: str | MISSING = Field(MISSING, examples=[""])


class GetItemListRequest(PageParams):
    null_fields: ClassVar[set] = {"status"}

    status: ItemStatusEnum | None = Field(None, examples=[ItemStatusEnum.ACTIVE])


class BatchCreateItemRequest(BaseRequest):
    items: list[CreateOptionRequest] = Field(..., examples=[[{"name": "example"}]])

    @field_validator("items")
    @classmethod
    def within_batch_size(cls, value: list[CreateOptionRequest]) -> list[CreateOptionRequest]:
        if len(value) > MAX_BATCH_SIZE:
            raise ValueError(f"한 번에 요청할 수 있는 항목 수는 {MAX_BATCH_SIZE}개 이하입니다")
        return value
```

### 필드 규칙

Request와 DTO의 같은 필드는 같은 제약을 사용합니다.

Request 필드에는 DTO 대신 Scalar 타입이나 Request 모델을 사용합니다.

명시적 `null` 허용 필드는 `null_fields`에 선언합니다.

`null_fields`에 선언한 필드의 빈 문자열은 `None`으로 변환합니다.

빈 문자열 유지 필드는 `empty_str_fields`에 선언합니다.

선언하지 않은 필드의 명시적 `null`과 빈 문자열은 거부합니다.

## Router

### 부분 수정

```python
@router.patch(
    "/items/{item_id:uuid}",
    name="항목 수정",
    response_model=BaseResponse,
)
@inject
async def update_item(
    item_id: UUID,
    body: UpdateItemRequest,
    use_case: Annotated[
        UpdateItemUseCase,
        Depends(Provide[AppContainer.item.update_item_command]),
    ],
) -> BaseResponse:
    data = UpdateItemDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="항목 수정 성공",
        data=await use_case.execute(item_id=item_id, data=data),
    )
```

PATCH Request는 `MISSING`과 `exclude_unset=True`로 전달된 필드만 구분합니다.

부분 수정 경로는 PATCH로만 정의합니다.

### 핸들러 이름

조회 핸들러 이름은 `get_by_id`, `get_list`처럼 동작만 작성하고, 같은 파일에서 이름이 겹치면 리소스 이름을 붙입니다.

### Query Parameter

```python
query: Annotated[GetItemListRequest, Query()]
```

`Depends`, `Query`, `Header`는 `Annotated`로 선언합니다.

### 단일 필드 교체

PUT Request는 필수 Nullable 필드로 전체 교체 의도를 구분합니다.

```python
class ReplaceItemParentRequest(BaseRequest):
    null_fields: ClassVar[set] = {"parent_id"}

    parent_id: UUID | None = Field(
        ...,
        examples=["01900000-0000-7000-8000-000000000000", None],
    )
```

## Repository

### 조회와 변경

```python
class ItemSQLAlchemyRepo(IItemRepo):
    async def get_by_id(self, *, item_id: UUID) -> Item | None:
        stmt = select(Item).where(Item.id == item_id)

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_list(
        self,
        *,
        prev: int,
        limit: int,
        status: ItemStatusEnum | None,
    ) -> list[Item]:
        async with session_factory() as read_session:
            stmt = select(Item)
            if status is not None:
                stmt = stmt.where(Item.status == status)
            stmt = stmt.order_by(Item.created_at.desc()).offset(prev).limit(limit)

            result = await read_session.execute(stmt)

            return list(result.scalars().all())

    async def exists_by_name(self, *, name: str) -> bool:
        async with session_factory() as read_session:
            stmt = select(Item.id).where(Item.name == name).limit(1)

            result = await read_session.execute(stmt)

            return result.scalar_one_or_none() is not None

    async def detach_tags(self, *, item_ids: list[UUID]) -> None:
        if not item_ids:
            return

        stmt = delete(item_tag_table).where(item_tag_table.c.item_id.in_(item_ids))

        await session.execute(stmt)

    async def detach_parent(self, *, item_ids: list[UUID]) -> None:
        if not item_ids:
            return

        stmt = update(Item).where(Item.id.in_(item_ids)).values(parent_id=None)

        await session.execute(stmt)
```

사용자 식별 인자 이름은 컬럼 이름과 무관하게 `user_id`로 작성합니다.

### 빈 Collection 입력

```python
async def get_by_ids(self, *, item_ids: list[UUID]) -> list[Item]:
    if not item_ids:
        return []

    stmt = select(Item).where(Item.id.in_(item_ids))

    result = await session.execute(stmt)

    return list(result.scalars().all())
```

선택 Collection 필터는 `list[UUID] | None`으로 선언합니다. `None`은 필터 없음, 빈 목록은 DB 조회 없는 빈 결과입니다.

## 논리 삭제

### 기본 조회

모든 ORM SELECT에 논리 삭제 필터를 적용합니다.

### 삭제 항목 조회

```python
stmt = select(Item).execution_options(include_deleted=True)
```

### 서브쿼리 대상


| 대상           | 사용 객체      |
| ------------ | ---------- |
| 논리 삭제 Entity | ORM Entity |
| 순수 연관 테이블    | Core Table |


## SQLAlchemy Mapping

### 선언

```python
def init_item_mappers() -> None:
    from app.example.domain.entities.item import Item, ItemOption

    mapper_registry.map_imperatively(
        Item,
        item_table,
        version_id_col=item_table.c.version_id,
        properties={
            "options": relationship(
                ItemOption,
                viewonly=True,
                lazy="selectin",
                order_by=item_option_table.c.display_order,
                back_populates="item",
            ),
        },
    )
```

### Cardinality

`uselist` 인자는 생략합니다.

## SQLAlchemy Table

### 선언

```python
item_table = BaseTable(
    "items",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("parent_id", UUID, ForeignKey("items.id"), nullable=True, index=True),
    Column("name", String(100), nullable=False),
    Column("description", Text, nullable=True),
    Column("display_order", Integer, nullable=False, default=0, server_default="0"),
    Column("is_deleted", Boolean, nullable=False, default=False, server_default=false()),
)

item_tag_table = Table(
    "item_tags",
    metadata,
    Column("item_id", UUID, ForeignKey("items.id"), nullable=False),
    Column("tag_id", UUID, ForeignKey("tags.id"), nullable=False, index=True),
    PrimaryKeyConstraint("item_id", "tag_id"),
)
```

### 공통 컬럼

`BaseTable`은 `created_at`, `updated_at`, `version_id`를 선언합니다.

### 문자열 타입

최대 길이가 정해진 문자열은 `String(n)`으로 선언합니다.

최대 길이가 없는 자유 텍스트는 `Text`로 선언합니다.

### 테이블 이름

테이블 이름은 복수형 Snake Case로 작성합니다.

## Error

### Domain Error

```python
class DuplicateItemError(CustomError):
    code = 409
    error_code = "EXAMPLE__DUPLICATE_ITEM"
    message = "같은 항목이 이미 존재합니다."
```

### Core Error

```python
class InvalidValueError(CustomError):
    code = 400
    error_code = "COMMON__INVALID_VALUE"
    message = "값이 올바르지 않습니다."
```

### 발생

```python
if await self._item_repo.exists_by_name(name=data.name):
    raise DuplicateItemError

if value not in allowed_values:
    raise InvalidValueError(message=f"허용 값: {', '.join(allowed_values)}")
```

```text
Domain 코드       -> Domain Error
Application 코드  -> Application Error
Presentation 코드 -> Presentation Error
Core Error         -> 모든 레이어
```

## Helper

### 상태 없음

```python
def build_cache_key(*, prefix: str, key: str) -> str:
    return f"{prefix}:{key}"
```

### 상태 있음

```python
class CacheHelper:
    def __init__(self, *, client: CacheClient):
        self._client = client
```

## Service

```python
class StorageService(IStorageService):
    def __init__(self, *, client: StorageClient):
        self._client = client

    async def upload(self, *, path: str, data: bytes) -> None:
        await self._client.upload(path=path, data=data)
```

## Container

```python
class ItemContainer(containers.DeclarativeContainer):
    storage_client = providers.Dependency()
    storage_service = providers.Singleton(StorageService, client=storage_client)
    item_repo = providers.Singleton(ItemSQLAlchemyRepo)

    get_item_query = providers.Factory(GetItemUseCase, item_repo=item_repo)
    create_item_command = providers.Factory(CreateItemUseCase, item_repo=item_repo)
```

## 코드 표기

### Logger

```python
logger = logging.getLogger(__name__)
```

### 생성자와 반환 타입

```python
class ItemService:
    def __init__(self, *, item_repo: IItemRepo):
        self._item_repo = item_repo

    async def get_name(self, *, item_id: UUID) -> str:
        return f"항목 이름: {await self._item_repo.get_name(item_id=item_id)}"
```

미사용 인자 이름은 `_`로 작성합니다.

### Lint 예외

Ruff 예외는 사유 코드를 포함한 `# noqa: <code>`로 지정합니다.

### 주석

주석은 한국어로 작성합니다.

### 미사용 코드

사용처 없는 코드는 유지합니다.

미사용 코드에도 동일한 표기 규칙을 적용합니다.

## 실행 명령

```makefile
check:
	uv run ruff check --fix
	uv run ruff format --check
```
