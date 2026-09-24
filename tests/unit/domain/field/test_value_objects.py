import pytest

from src.domain.field.exceptions import (
    InvalidAreaRangeError,
    InvalidCoordinateError,
    PolygonNotClosedError,
    PolygonTooSmallError,
    SelfIntersectingPolygonError,
)
from src.domain.field.value_objects import Coordinate, FieldFilter, Polygon

# A small (~1.24 ha) valid closed square, roughly 111m x 111m at the equator.
VALID_SQUARE = (
    Coordinate(latitude=0.0, longitude=0.0),
    Coordinate(latitude=0.0, longitude=0.001),
    Coordinate(latitude=0.001, longitude=0.001),
    Coordinate(latitude=0.001, longitude=0.0),
    Coordinate(latitude=0.0, longitude=0.0),
)


def test_valid_closed_polygon_is_accepted() -> None:
    polygon = Polygon(vertices=VALID_SQUARE)
    assert polygon.area_ha >= 0.1


def test_open_polygon_is_rejected() -> None:
    open_ring = VALID_SQUARE[:-1] + (Coordinate(latitude=0.5, longitude=0.5),)
    with pytest.raises(PolygonNotClosedError):
        Polygon(vertices=open_ring)


def test_self_intersecting_polygon_is_rejected() -> None:
    bowtie = (
        Coordinate(latitude=0.0, longitude=0.0),
        Coordinate(latitude=0.001, longitude=0.001),
        Coordinate(latitude=0.0, longitude=0.001),
        Coordinate(latitude=0.001, longitude=0.0),
        Coordinate(latitude=0.0, longitude=0.0),
    )
    with pytest.raises(SelfIntersectingPolygonError):
        Polygon(vertices=bowtie)


def test_polygon_below_minimum_area_is_rejected() -> None:
    tiny_square = (
        Coordinate(latitude=0.0, longitude=0.0),
        Coordinate(latitude=0.0, longitude=0.00001),
        Coordinate(latitude=0.00001, longitude=0.00001),
        Coordinate(latitude=0.00001, longitude=0.0),
        Coordinate(latitude=0.0, longitude=0.0),
    )
    with pytest.raises(PolygonTooSmallError, match="below the required minimum"):
        Polygon(vertices=tiny_square)


def test_polygon_with_fewer_than_three_distinct_vertices_is_rejected() -> None:
    two_points = (
        Coordinate(latitude=0.0, longitude=0.0),
        Coordinate(latitude=0.001, longitude=0.001),
    )
    with pytest.raises(PolygonNotClosedError):
        Polygon(vertices=two_points)


def test_coordinate_out_of_range_latitude_is_rejected() -> None:
    with pytest.raises(InvalidCoordinateError):
        Coordinate(latitude=91.0, longitude=0.0)


def test_coordinate_out_of_range_longitude_is_rejected() -> None:
    with pytest.raises(InvalidCoordinateError):
        Coordinate(latitude=0.0, longitude=181.0)


def test_field_filter_with_only_crop_is_valid() -> None:
    filter_ = FieldFilter(crop="wheat")
    assert filter_.crop == "wheat"
    assert filter_.owner is None


def test_field_filter_with_only_owner_is_valid() -> None:
    filter_ = FieldFilter(owner="Ivan")
    assert filter_.owner == "Ivan"
    assert filter_.crop is None


def test_field_filter_with_crop_and_owner_is_valid() -> None:
    filter_ = FieldFilter(crop="wheat", owner="Ivan")
    assert filter_.crop == "wheat"
    assert filter_.owner == "Ivan"


def test_field_filter_empty_is_valid() -> None:
    filter_ = FieldFilter()
    assert filter_.crop is None
    assert filter_.owner is None
    assert filter_.min_area_ha is None
    assert filter_.max_area_ha is None


def test_field_filter_with_only_min_area_is_valid() -> None:
    filter_ = FieldFilter(min_area_ha=0.5)
    assert filter_.min_area_ha == 0.5
    assert filter_.max_area_ha is None


def test_field_filter_with_only_max_area_is_valid() -> None:
    filter_ = FieldFilter(max_area_ha=2.0)
    assert filter_.max_area_ha == 2.0
    assert filter_.min_area_ha is None


def test_field_filter_with_valid_area_range_is_valid() -> None:
    filter_ = FieldFilter(min_area_ha=0.5, max_area_ha=2.0)
    assert filter_.min_area_ha == 0.5
    assert filter_.max_area_ha == 2.0


def test_field_filter_with_inverted_area_range_is_rejected() -> None:
    with pytest.raises(InvalidAreaRangeError, match="greater than maximum"):
        FieldFilter(min_area_ha=5.0, max_area_ha=1.0)


def test_polygon_centroid_is_center_of_square() -> None:
    centroid = Polygon(vertices=VALID_SQUARE).centroid
    assert centroid.latitude == pytest.approx(0.0005)
    assert centroid.longitude == pytest.approx(0.0005)


def test_distance_to_same_point_is_zero() -> None:
    point = Coordinate(latitude=50.45, longitude=30.52)
    assert point.distance_to_m(point) == pytest.approx(0.0, abs=1e-6)


def test_distance_is_geodesic_meters() -> None:
    # One degree of latitude along a meridian is ~110.6 km near the equator.
    a = Coordinate(latitude=0.0, longitude=0.0)
    b = Coordinate(latitude=1.0, longitude=0.0)
    assert a.distance_to_m(b) == pytest.approx(110_574, rel=1e-3)
    assert a.distance_to_m(b) == pytest.approx(b.distance_to_m(a))
