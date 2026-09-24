import uuid
from datetime import UTC, datetime

from src.application.field.find_fields_by_point import FindFieldsByPointUseCase
from src.domain.common.pagination import Page, PageRequest
from src.domain.field.entities import Field
from src.domain.field.repository import FieldRepository
from src.domain.field.value_objects import Coordinate, FieldFilter, Polygon


def _square(min_lat: float, min_lon: float, side: float) -> Polygon:
    return Polygon(
        vertices=(
            Coordinate(latitude=min_lat, longitude=min_lon),
            Coordinate(latitude=min_lat, longitude=min_lon + side),
            Coordinate(latitude=min_lat + side, longitude=min_lon + side),
            Coordinate(latitude=min_lat + side, longitude=min_lon),
            Coordinate(latitude=min_lat, longitude=min_lon),
        )
    )


def _field(name: str, geometry: Polygon) -> Field:
    return Field.create(
        id=uuid.uuid4(),
        name=name,
        owner="Owner",
        crop="wheat",
        geometry=geometry,
        created_at=datetime.now(UTC),
    )


class _FakeRepository(FieldRepository):
    def __init__(self, containing: list[Field]) -> None:
        self._containing = containing

    def save(self, field: Field) -> None:
        raise NotImplementedError

    def find_containing_point(self, point: Coordinate) -> list[Field]:
        return list(self._containing)

    def find_page(self, filter: FieldFilter, page_request: PageRequest) -> Page[Field]:
        raise NotImplementedError

    def find_by_id(self, field_id: uuid.UUID) -> Field | None:
        raise NotImplementedError


def test_matches_are_sorted_by_distance_to_field_center() -> None:
    far = _field("Far", _square(0.0, 0.0, 0.02))  # center (0.01, 0.01)
    near = _field("Near", _square(0.0045, 0.0045, 0.002))  # center (0.0055, 0.0055)
    use_case = FindFieldsByPointUseCase(_FakeRepository([far, near]))

    matches = use_case.execute(Coordinate(latitude=0.005, longitude=0.005))

    assert [m.field.name for m in matches] == ["Near", "Far"]
    assert matches[0].distance_to_center_m < matches[1].distance_to_center_m


def test_distance_is_zero_at_field_center() -> None:
    field = _field("Centered", _square(0.0, 0.0, 0.01))
    use_case = FindFieldsByPointUseCase(_FakeRepository([field]))

    [match] = use_case.execute(Coordinate(latitude=0.005, longitude=0.005))

    assert match.distance_to_center_m < 0.01


def test_no_containing_fields_returns_empty_list() -> None:
    use_case = FindFieldsByPointUseCase(_FakeRepository([]))
    assert use_case.execute(Coordinate(latitude=1.0, longitude=1.0)) == []
