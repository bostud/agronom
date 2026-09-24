from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.field.entities import Field
from src.domain.field.repository import FieldRepository
from src.domain.field.value_objects import Polygon


@dataclass(frozen=True)
class CreateFieldCommand:
    name: str | None
    owner: str | None
    crop: str | None
    geometry: Polygon | None


class CreateFieldUseCase:
    def __init__(self, repository: FieldRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateFieldCommand) -> Field:
        field = Field.create(
            id=uuid.uuid4(),
            name=command.name,
            owner=command.owner,
            crop=command.crop,
            geometry=command.geometry,
            created_at=datetime.now(UTC),
        )
        self._repository.save(field)
        return field
