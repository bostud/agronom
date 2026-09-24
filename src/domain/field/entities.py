from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.field.exceptions import MissingFieldAttributeError
from src.domain.field.value_objects import Polygon


class Field(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    owner: str
    crop: str
    geometry: Polygon
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        id: uuid.UUID,
        name: str | None,
        owner: str | None,
        crop: str | None,
        geometry: Polygon | None,
        created_at: datetime,
    ) -> "Field":
        missing = [
            attr
            for attr, value in (
                ("name", name),
                ("owner", owner),
                ("crop", crop),
                ("geometry", geometry),
            )
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise MissingFieldAttributeError(
                f"Missing required field(s): {', '.join(missing)}."
            )
        assert name is not None
        assert owner is not None
        assert crop is not None
        assert geometry is not None
        return cls(
            id=id,
            name=name,
            owner=owner,
            crop=crop,
            geometry=geometry,
            created_at=created_at,
        )

    @property
    def area_ha(self) -> float:
        return self.geometry.area_ha
