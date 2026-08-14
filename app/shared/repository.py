from collections.abc import Sequence
from typing import Any, Protocol

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.shared.pagination import PaginatedResult, PaginationParams


class RepositoryProtocol[ModelType: DeclarativeBase](Protocol):
    """Generic repository protocol contract for domain entities."""

    async def create(self, obj_in: ModelType, autocommit: bool = True) -> ModelType: ...
    async def get(self, id: Any) -> ModelType | None: ...
    async def get_all(self) -> Sequence[ModelType]: ...
    async def delete(self, obj_in: ModelType, autocommit: bool = True) -> None: ...
    async def update_partial(
        self,
        db_obj: ModelType,
        obj_in: dict[str, Any] | PydanticBaseModel,
        autocommit: bool = True,
    ) -> ModelType: ...
    async def paginate(
        self,
        params: PaginationParams,
        query: Select | None = None,
    ) -> PaginatedResult[ModelType]: ...


class BaseRepository[ModelType: DeclarativeBase]:
    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def create(self, obj_in: ModelType, autocommit: bool = True) -> ModelType:
        self.session.add(obj_in)
        if autocommit:
            await self.session.commit()
            await self.session.refresh(obj_in)
        else:
            await self.session.flush()
        return obj_in

    async def get(self, id: Any) -> ModelType | None:
        return await self.session.get(self.model, id)

    async def get_all(self) -> Sequence[ModelType]:
        query = select(self.model)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete(self, obj_in: ModelType, autocommit: bool = True) -> None:
        await self.session.delete(obj_in)
        if autocommit:
            await self.session.commit()
        else:
            await self.session.flush()

    async def update_partial(
        self,
        db_obj: ModelType,
        obj_in: dict[str, Any] | PydanticBaseModel,
        autocommit: bool = True,
    ) -> ModelType:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.session.add(db_obj)
        if autocommit:
            await self.session.commit()
            await self.session.refresh(db_obj)
        else:
            await self.session.flush()
        return db_obj

    async def paginate(
        self,
        params: PaginationParams,
        query: Select | None = None,
    ) -> PaginatedResult[ModelType]:
        """Performs optimized COUNT and LIMIT/OFFSET pagination."""
        base_query = query if query is not None else select(self.model)

        # Build efficient scalar count query without loading model records
        count_subquery = base_query.order_by(None).subquery()
        count_query = select(func.count()).select_from(count_subquery)
        total_count = await self.session.scalar(count_query) or 0

        # Apply LIMIT and OFFSET
        paginated_query = base_query.offset(params.offset).limit(params.limit)
        result = await self.session.execute(paginated_query)
        items = result.scalars().all()

        return PaginatedResult(
            items=items,
            total=total_count,
            page=params.page,
            size=params.size,
        )
