from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.field.create_field import CreateFieldCommand, CreateFieldUseCase
from src.application.field.find_fields_by_point import FindFieldsByPointUseCase
from src.application.field.get_field_by_id import GetFieldByIdUseCase
from src.application.field.list_fields import ListFieldsUseCase
from src.domain.common.pagination import DEFAULT_LIMIT, DEFAULT_OFFSET, PageRequest
from src.domain.field.exceptions import (
    FieldNotFoundError,
    InvalidAreaRangeError,
    InvalidCoordinateError,
    InvalidPageRequestError,
    MissingFieldAttributeError,
    PolygonNotClosedError,
    PolygonTooSmallError,
    SelfIntersectingPolygonError,
)
from src.domain.field.value_objects import Coordinate, FieldFilter
from src.presentation.api.dependencies import (
    get_create_field_use_case,
    get_find_fields_by_point_use_case,
    get_get_field_by_id_use_case,
    get_list_fields_use_case,
)
from src.presentation.api.schemas import (
    CreateFieldRequest,
    FieldListResponse,
    FieldResponse,
    FieldPointMatch,
    FieldSearchResponse,
    QueryPoint,
)

router = APIRouter(prefix="/fields", tags=["fields"])


@router.post("", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(
    request: CreateFieldRequest,
    use_case: CreateFieldUseCase = Depends(get_create_field_use_case),
) -> FieldResponse:
    try:
        geometry = request.geometry.to_domain()
    except (
        PolygonNotClosedError,
        SelfIntersectingPolygonError,
        PolygonTooSmallError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        command = CreateFieldCommand(
            name=request.name,
            owner=request.owner,
            crop=request.crop,
            geometry=geometry,
        )
        field = use_case.execute(command)
    except MissingFieldAttributeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return FieldResponse.from_domain(field)


@router.get("", response_model=FieldListResponse)
def list_fields(
    crop: str | None = None,
    owner: str | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    use_case: ListFieldsUseCase = Depends(get_list_fields_use_case),
) -> FieldListResponse:
    try:
        page_request = PageRequest(limit=limit, offset=offset)
    except InvalidPageRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        field_filter = FieldFilter(
            crop=crop, owner=owner, min_area_ha=min_area, max_area_ha=max_area
        )
    except InvalidAreaRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = use_case.execute(field_filter, page_request)
    return FieldListResponse.from_domain(result)


@router.get("/find-by-point", response_model=FieldSearchResponse)
def find_fields_by_point(
    lat: float,
    lon: float,
    use_case: FindFieldsByPointUseCase = Depends(get_find_fields_by_point_use_case),
) -> FieldSearchResponse:
    try:
        point = Coordinate(latitude=lat, longitude=lon)
    except InvalidCoordinateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    started = time.perf_counter()
    matches = use_case.execute(point)
    query_time_ms = (time.perf_counter() - started) * 1000

    return FieldSearchResponse(
        query_point=QueryPoint(lon=lon, lat=lat),
        fields=[
            FieldPointMatch.from_domain(match.field, match.distance_to_center_m)
            for match in matches
        ],
        query_time_ms=query_time_ms,
    )


@router.get("/{field_id}", response_model=FieldResponse)
def get_field(
    field_id: uuid.UUID,
    use_case: GetFieldByIdUseCase = Depends(get_get_field_by_id_use_case),
) -> FieldResponse:
    try:
        field = use_case.execute(field_id)
    except FieldNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FieldResponse.from_domain(field)
