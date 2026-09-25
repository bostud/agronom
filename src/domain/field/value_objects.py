from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator
from pyproj import Geod
from shapely.geometry import Polygon as ShapelyPolygon

from src.domain.field.exceptions import (
    InvalidAreaRangeError,
    InvalidCoordinateError,
    PolygonNotClosedError,
    PolygonTooSmallError,
    SelfIntersectingPolygonError,
)
from src.settings import GEOD_ELLIPSOID, MIN_POLYGON_AREA_HA, SQ_METERS_PER_HECTARE

_GEOD = Geod(ellps=GEOD_ELLIPSOID)


class Coordinate(BaseModel):
    model_config = ConfigDict(frozen=True)

    latitude: float
    longitude: float

    @model_validator(mode="after")
    def _validate_range(self) -> "Coordinate":
        if not (-90.0 <= self.latitude <= 90.0):
            raise InvalidCoordinateError(
                f"Latitude {self.latitude} is out of range [-90.0, 90.0]."
            )
        if not (-180.0 <= self.longitude <= 180.0):
            raise InvalidCoordinateError(
                f"Longitude {self.longitude} is out of range [-180.0, 180.0]."
            )
        return self

    def distance_to_m(self, other: "Coordinate") -> float:
        _fwd_az, _back_az, distance_m = _GEOD.inv(
            self.longitude, self.latitude, other.longitude, other.latitude
        )
        return float(distance_m)


class Polygon(BaseModel):
    model_config = ConfigDict(frozen=True)

    vertices: tuple[Coordinate, ...]

    @model_validator(mode="after")
    def _validate_geometry(self) -> "Polygon":
        is_closed = self._is_closed_ring()
        distinct_ring = self.vertices[:-1] if is_closed else self.vertices
        if len(distinct_ring) < 3:
            raise PolygonNotClosedError(
                "Polygon must have at least 3 distinct vertices before closure."
            )
        if not is_closed:
            raise PolygonNotClosedError(
                "Polygon geometry is not closed: first and last points do not match."
            )
        
        shapely_polygon = self._to_shapely()
        if not shapely_polygon.is_simple:
            raise SelfIntersectingPolygonError("Polygon geometry edges self-intersect.")

        area = self._geodesic_area_ha(shapely_polygon)
        if area < MIN_POLYGON_AREA_HA:
            raise PolygonTooSmallError(
                f"Polygon area is {area:.4f} ha, below the required minimum of "
                f"{MIN_POLYGON_AREA_HA} ha."
            )
        return self

    def _is_closed_ring(self) -> bool:
        if len(self.vertices) < 2:
            return False
        first, last = self.vertices[0], self.vertices[-1]
        return first.latitude == last.latitude and first.longitude == last.longitude

    def _to_shapely(self) -> ShapelyPolygon:
        coords = [(c.longitude, c.latitude) for c in self.vertices]
        return ShapelyPolygon(coords)

    @staticmethod
    def _geodesic_area_ha(shapely_polygon: ShapelyPolygon) -> float:
        area_m2, _perimeter_m = _GEOD.geometry_area_perimeter(shapely_polygon)
        return abs(area_m2) / SQ_METERS_PER_HECTARE

    @property
    def area_ha(self) -> float:
        return self._geodesic_area_ha(self._to_shapely())

    @property
    def centroid(self) -> Coordinate:
        center = self._to_shapely().centroid
        return Coordinate(latitude=center.y, longitude=center.x)


class FieldFilter(BaseModel):
    model_config = ConfigDict(frozen=True)

    crop: str | None = None
    owner: str | None = None
    min_area_ha: float | None = None
    max_area_ha: float | None = None

    @model_validator(mode="after")
    def _validate_area_range(self) -> "FieldFilter":
        if (
            self.min_area_ha is not None
            and self.max_area_ha is not None
            and self.min_area_ha > self.max_area_ha
        ):
            raise InvalidAreaRangeError(
                f"Minimum area {self.min_area_ha} ha is greater than maximum area "
                f"{self.max_area_ha} ha."
            )
        return self
