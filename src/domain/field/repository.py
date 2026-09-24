from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.common.pagination import Page, PageRequest
from src.domain.field.entities import Field
from src.domain.field.value_objects import Coordinate, FieldFilter


class FieldRepository(ABC):
    @abstractmethod
    def save(self, field: Field) -> None: ...

    @abstractmethod
    def find_containing_point(self, point: Coordinate) -> list[Field]: ...

    @abstractmethod
    def find_page(
        self, filter: FieldFilter, page_request: PageRequest
    ) -> Page[Field]: ...

    @abstractmethod
    def find_by_id(self, field_id: uuid.UUID) -> Field | None: ...
