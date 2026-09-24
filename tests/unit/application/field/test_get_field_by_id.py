import uuid
from datetime import UTC, datetime

import pytest

from src.application.field.get_field_by_id import GetFieldByIdUseCase
from src.domain.common.pagination import Page, PageRequest
from src.domain.field.entities import Field
from src.domain.field.exceptions import FieldNotFoundError
from src.domain.field.repository import FieldRepository
from src.domain.field.value_objects import Coordinate, FieldFilter, Polygon

VALID_GEOMETRY = Polygon(
    vertices=(
        Coordinate(latitude=0.0, longitude=0.0),
        Coordinate(latitude=0.0, longitude=0.001),
        Coordinate(latitude=0.001, longitude=0.001),
        Coordinate(latitude=0.001, longitude=0.0),
        Coordinate(latitude=0.0, longitude=0.0),
    )
)


class FakeFieldRepository(FieldRepository):
    def __init__(self, fields: dict[uuid.UUID, Field]) -> None:
        self._fields = fields

    def save(self, field: Field) -> None:
        self._fields[field.id] = field

    def find_containing_point(self, point: Coordinate) -> list[Field]:
        return []

    def find_page(self, filter: FieldFilter, page_request: PageRequest) -> Page[Field]:
        return Page(items=(), total=0, limit=page_request.limit, offset=page_request.offset)

    def find_by_id(self, field_id: uuid.UUID) -> Field | None:
        return self._fields.get(field_id)


def _make_field() -> Field:
    return Field.create(
        id=uuid.uuid4(),
        name="North Forty",
        owner="Ivan Bondarenko",
        crop="wheat",
        geometry=VALID_GEOMETRY,
        created_at=datetime.now(UTC),
    )


def test_get_field_by_id_returns_the_matching_field() -> None:
    field = _make_field()
    repository = FakeFieldRepository({field.id: field})
    use_case = GetFieldByIdUseCase(repository)

    result = use_case.execute(field.id)

    assert result == field


def test_get_field_by_id_raises_not_found_when_no_match() -> None:
    repository = FakeFieldRepository({})
    use_case = GetFieldByIdUseCase(repository)

    missing_id = uuid.uuid4()

    with pytest.raises(FieldNotFoundError) as exc_info:
        use_case.execute(missing_id)

    assert str(exc_info.value) == f"No field found with id {missing_id}."


def test_get_field_by_id_returns_only_the_requested_field() -> None:
    wanted = _make_field()
    other = _make_field()
    repository = FakeFieldRepository({wanted.id: wanted, other.id: other})
    use_case = GetFieldByIdUseCase(repository)

    assert use_case.execute(wanted.id) == wanted
    assert use_case.execute(other.id) == other
