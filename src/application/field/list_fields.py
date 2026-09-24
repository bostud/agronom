from __future__ import annotations

from src.domain.common.pagination import Page, PageRequest
from src.domain.field.entities import Field
from src.domain.field.repository import FieldRepository
from src.domain.field.value_objects import FieldFilter


class ListFieldsUseCase:
    def __init__(self, repository: FieldRepository) -> None:
        self._repository = repository

    def execute(self, filter: FieldFilter, page_request: PageRequest) -> Page[Field]:
        return self._repository.find_page(filter, page_request)
