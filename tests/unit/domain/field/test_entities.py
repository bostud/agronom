import uuid
from datetime import UTC, datetime

import pytest

from src.domain.field.entities import Field
from src.domain.field.exceptions import MissingFieldAttributeError
from src.domain.field.value_objects import Coordinate, Polygon

VALID_BOUNDARY = Polygon(
    vertices=(
        Coordinate(latitude=0.0, longitude=0.0),
        Coordinate(latitude=0.0, longitude=0.001),
        Coordinate(latitude=0.001, longitude=0.001),
        Coordinate(latitude=0.001, longitude=0.0),
        Coordinate(latitude=0.0, longitude=0.0),
    )
)


def _create(**overrides: object) -> Field:
    kwargs: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": "North Forty",
        "owner": "Ivan Bondarenko",
        "crop": "wheat",
        "geometry": VALID_BOUNDARY,
        "created_at": datetime.now(UTC),
    }
    kwargs.update(overrides)
    return Field.create(**kwargs)  # type: ignore[arg-type]


def test_field_with_all_attributes_is_created() -> None:
    field = _create()
    assert field.name == "North Forty"
    assert field.area_ha >= 0.1


@pytest.mark.parametrize("missing_attr", ["name", "owner", "crop", "geometry"])
def test_field_missing_a_required_attribute_is_rejected(missing_attr: str) -> None:
    with pytest.raises(MissingFieldAttributeError, match=missing_attr):
        _create(**{missing_attr: None})


def test_field_missing_multiple_attributes_names_all_in_one_error() -> None:
    with pytest.raises(MissingFieldAttributeError, match="name") as exc_info:
        _create(name=None, owner=None)
    assert "owner" in str(exc_info.value)


def test_field_with_blank_string_attribute_is_rejected() -> None:
    with pytest.raises(MissingFieldAttributeError, match="owner"):
        _create(owner="   ")
