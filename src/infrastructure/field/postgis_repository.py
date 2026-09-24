from __future__ import annotations

import uuid

from geoalchemy2.functions import ST_Contains
from geoalchemy2.shape import from_shape
from shapely.geometry import Point as ShapelyPoint
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from src.domain.common.pagination import Page, PageRequest
from src.domain.field.entities import Field
from src.domain.field.repository import FieldRepository
from src.domain.field.value_objects import Coordinate, FieldFilter
from src.infrastructure.field.mappers import field_to_model, model_to_field
from src.infrastructure.field.models import FieldModel


class PostgisFieldRepository(FieldRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, field: Field) -> None:
        self._session.add(field_to_model(field))
        self._session.flush()

    def find_containing_point(self, point: Coordinate) -> list[Field]:
        shapely_point = ShapelyPoint(point.longitude, point.latitude)
        search_point = from_shape(shapely_point, srid=4326)
        stmt = select(FieldModel).where(
            FieldModel.geometry.bool_op("&&")(search_point),
            ST_Contains(FieldModel.geometry, search_point),
        )
        models = self._session.execute(stmt).scalars().all()
        return [model_to_field(model) for model in models]

    def find_page(self, filter: FieldFilter, page_request: PageRequest) -> Page[Field]:
        conditions = self._build_filter_conditions(filter)

        count_stmt = select(func.count()).select_from(FieldModel)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = self._session.execute(count_stmt).scalar_one()

        page_stmt = (
            select(FieldModel)
            .order_by(FieldModel.name.asc(), FieldModel.id.asc())
            .limit(page_request.limit)
            .offset(page_request.offset)
        )
        if conditions:
            page_stmt = page_stmt.where(*conditions)
        models = self._session.execute(page_stmt).scalars().all()

        return Page(
            items=tuple(model_to_field(model) for model in models),
            total=total,
            limit=page_request.limit,
            offset=page_request.offset,
        )

    def find_by_id(self, field_id: uuid.UUID) -> Field | None:
        model = self._session.get(FieldModel, field_id)
        if model is None:
            return None
        return model_to_field(model)

    @staticmethod
    def _build_filter_conditions(filter: FieldFilter) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if filter.crop is not None:
            conditions.append(func.lower(FieldModel.crop) == filter.crop.lower())
        if filter.owner is not None:
            conditions.append(FieldModel.owner.ilike(f"%{filter.owner}%"))
        if filter.min_area_ha is not None:
            conditions.append(FieldModel.area_ha >= filter.min_area_ha)
        if filter.max_area_ha is not None:
            conditions.append(FieldModel.area_ha <= filter.max_area_ha)
        return conditions
