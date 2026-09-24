from __future__ import annotations

import uuid

from src.domain.field.entities import Field
from src.domain.field.exceptions import FieldNotFoundError
from src.domain.field.repository import FieldRepository


class GetFieldByIdUseCase:
    def __init__(self, repository: FieldRepository) -> None:
        self._repository = repository

    def execute(self, field_id: uuid.UUID) -> Field:
        field = self._repository.find_by_id(field_id)
        if field is None:
            raise FieldNotFoundError(f"No field found with id {field_id}.")
        return field
