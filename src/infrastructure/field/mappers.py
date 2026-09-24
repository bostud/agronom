from __future__ import annotations

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Polygon as ShapelyPolygon

from src.domain.field.entities import Field
from src.domain.field.value_objects import Coordinate, Polygon
from src.infrastructure.field.models import FieldModel


def field_to_model(field: Field) -> FieldModel:
    shapely_polygon = ShapelyPolygon(
        [(coordinate.longitude, coordinate.latitude) for coordinate in field.geometry.vertices]
    )
    return FieldModel(
        id=field.id,
        name=field.name,
        owner=field.owner,
        crop=field.crop,
        geometry=from_shape(shapely_polygon, srid=4326),
        area_ha=field.area_ha,
        created_at=field.created_at,
    )


def model_to_field(model: FieldModel) -> Field:
    shapely_polygon = to_shape(model.geometry)
    vertices = tuple(
        Coordinate(latitude=lat, longitude=lon)
        for lon, lat in shapely_polygon.exterior.coords
    )
    geometry = Polygon(vertices=vertices)
    return Field(
        id=model.id,
        name=model.name,
        owner=model.owner,
        crop=model.crop,
        geometry=geometry,
        created_at=model.created_at,
    )
