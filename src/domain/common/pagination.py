from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator

from src.domain.field.exceptions import InvalidPageRequestError
from src.settings import DEFAULT_LIMIT, DEFAULT_OFFSET, MAX_LIMIT

T = TypeVar("T")


class PageRequest(BaseModel):
    """A limit/offset window over an ordered result set."""

    model_config = ConfigDict(frozen=True)

    limit: int = DEFAULT_LIMIT
    offset: int = DEFAULT_OFFSET

    @model_validator(mode="after")
    def _validate_bounds(self) -> "PageRequest":
        if not (1 <= self.limit <= MAX_LIMIT):
            raise InvalidPageRequestError(f"Limit must be between 1 and {MAX_LIMIT}.")
        if self.offset < 0:
            raise InvalidPageRequestError("Offset must be 0 or greater.")
        return self


class Page(BaseModel, Generic[T]):
    """A window of items plus the total number of items matching the query."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    items: tuple[T, ...]
    total: int
    limit: int
    offset: int
