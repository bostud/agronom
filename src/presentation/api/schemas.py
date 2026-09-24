from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from src.domain.common.pagination import Page
from src.domain.field.entities import Field
from src.domain.field.value_objects import Coordinate, Polygon


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[tuple[float, float]]]

    def to_domain(self) -> Polygon:
        ring = self.coordinates[0] if self.coordinates else []
        vertices = tuple(Coordinate(latitude=lat, longitude=lon) for lon, lat in ring)
        return Polygon(vertices=vertices)

    @classmethod
    def from_domain(cls, polygon: Polygon) -> "GeoJSONPolygon":
        ring = [(coordinate.longitude, coordinate.latitude) for coordinate in polygon.vertices]
        return cls(coordinates=[ring])


class CreateFieldRequest(BaseModel):
    name: str
    owner: str
    crop: str
    geometry: GeoJSONPolygon


class FieldResponse(BaseModel):
    id: uuid.UUID
    name: str
    geometry: GeoJSONPolygon
    area_ha: float
    crop: str
    owner: str
    created_at: datetime

    @classmethod
    def from_domain(cls, field: Field) -> "FieldResponse":
        return cls(
            id=field.id,
            name=field.name,
            owner=field.owner,
            crop=field.crop,
            geometry=GeoJSONPolygon.from_domain(field.geometry),
            area_ha=field.area_ha,
            created_at=field.created_at,
        )


class QueryPoint(BaseModel):
    lon: float
    lat: float


class FieldPointMatch(BaseModel):
    id: uuid.UUID
    name: str
    area_ha: float
    crop: str
    owner: str
    distance_to_center_m: float

    @classmethod
    def from_domain(cls, field: Field, distance_to_center_m: float) -> "FieldPointMatch":
        return cls(
            id=field.id,
            name=field.name,
            area_ha=field.area_ha,
            crop=field.crop,
            owner=field.owner,
            distance_to_center_m=distance_to_center_m,
        )


class FieldSearchResponse(BaseModel):
    query_point: QueryPoint
    fields: list[FieldPointMatch]
    query_time_ms: float


class FieldSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    area_ha: float
    crop: str
    owner: str

    @classmethod
    def from_domain(cls, field: Field) -> "FieldSummaryResponse":
        return cls(
            id=field.id,
            name=field.name,
            area_ha=field.area_ha,
            crop=field.crop,
            owner=field.owner,
        )


class FieldListResponse(BaseModel):
    total: int
    fields: list[FieldSummaryResponse]

    @classmethod
    def from_domain(cls, page: Page[Field]) -> "FieldListResponse":
        return cls(
            total=page.total,
            fields=[FieldSummaryResponse.from_domain(field) for field in page.items],
        )
