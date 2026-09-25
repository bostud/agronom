import pytest
from pydantic import ValidationError

from src.domain.common.pagination import PageRequest
from src.domain.field.exceptions import InvalidPageRequestError
from src.settings import DEFAULT_LIMIT, DEFAULT_OFFSET


def test_valid_page_request_is_accepted() -> None:
    page_request = PageRequest(limit=20, offset=40)
    assert page_request.limit == 20
    assert page_request.offset == 40


def test_defaults_are_limit_20_offset_0() -> None:
    page_request = PageRequest()
    assert page_request.limit == DEFAULT_LIMIT == 20
    assert page_request.offset == DEFAULT_OFFSET == 0


def test_offset_need_not_align_with_limit() -> None:
    page_request = PageRequest(limit=10, offset=7)
    assert page_request.offset == 7


@pytest.mark.parametrize("limit", [1, 100])
def test_limit_bounds_are_inclusive(limit: int) -> None:
    assert PageRequest(limit=limit, offset=0).limit == limit


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_limit_out_of_range_is_rejected(limit: int) -> None:
    with pytest.raises(InvalidPageRequestError, match="Limit must be between 1 and 100"):
        PageRequest(limit=limit, offset=0)


def test_negative_offset_is_rejected() -> None:
    with pytest.raises(InvalidPageRequestError, match="Offset must be 0 or greater"):
        PageRequest(limit=20, offset=-1)


def test_page_request_is_immutable() -> None:
    page_request = PageRequest(limit=20, offset=0)
    with pytest.raises(ValidationError):
        page_request.limit = 50  # type: ignore[misc]
