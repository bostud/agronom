from __future__ import annotations

from dataclasses import dataclass

from src.domain.field.entities import Field
from src.domain.field.repository import FieldRepository
from src.domain.field.value_objects import Coordinate


@dataclass(frozen=True)
class FieldMatch:
    field: Field
    distance_to_center_m: float


class FindFieldsByPointUseCase:
    def __init__(self, repository: FieldRepository) -> None:
        self._repository = repository

    def execute(self, point: Coordinate) -> list[FieldMatch]:
        matches = [
            FieldMatch(
                field=field,
                distance_to_center_m=point.distance_to_m(field.geometry.centroid),
            )
            for field in self._repository.find_containing_point(point)
        ]
        return sorted(matches, key=lambda match: match.distance_to_center_m)
