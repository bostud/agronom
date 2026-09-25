"""Populate the database with sample fields for manual testing and demos.

Fields are laid out on a grid of non-overlapping cells near Kyiv, so a point
inside any seeded field matches exactly that field.

Usage: python -m src.scripts.seed_fields --count 100 [--seed 42]
"""

from __future__ import annotations

import argparse
import math
import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.domain.field.entities import Field
from src.domain.field.value_objects import Coordinate, Polygon
from src.infrastructure.field.postgis_repository import PostgisFieldRepository
from src.settings import DATABASE_URL

ORIGIN_LAT = 50.0
ORIGIN_LON = 30.0
CELL_DEG = 0.01
# Each vertex sits between these fractions of a half-cell from the cell centre:
# the lower bound keeps the area well above the 0.1 ha minimum, the upper bound
# leaves a gap so neighbouring fields never touch.
MIN_VERTEX_OFFSET = 0.3
MAX_VERTEX_OFFSET = 0.9

CROPS = ("Пшениця", "Кукурудза", "Соняшник", "Ячмінь", "Ріпак", "Соя")
OWNERS = (
    "ФГ «Колос»",
    "ТОВ «Агро-Світанок»",
    "СФГ «Нива»",
    "Іванов І.І.",
    "Коваленко О.П.",
    "ПП «Зелений Гай»",
)


def _random_quad(center_lat: float, center_lon: float, rng: random.Random) -> Polygon:
    half = CELL_DEG / 2

    def offset() -> float:
        return rng.uniform(MIN_VERTEX_OFFSET, MAX_VERTEX_OFFSET) * half

    # One vertex per quadrant, counter-clockwise, so the ring never self-intersects.
    corners = (
        (center_lat - offset(), center_lon - offset()),
        (center_lat - offset(), center_lon + offset()),
        (center_lat + offset(), center_lon + offset()),
        (center_lat + offset(), center_lon - offset()),
    )
    vertices = tuple(
        Coordinate(latitude=round(lat, 6), longitude=round(lon, 6)) for lat, lon in corners
    )
    return Polygon(vertices=vertices + vertices[:1])


def seed_fields(session: Session, count: int, rng: random.Random) -> list[Field]:
    repository = PostgisFieldRepository(session)
    columns = math.ceil(math.sqrt(count))
    fields: list[Field] = []
    for index in range(count):
        row, column = divmod(index, columns)
        field = Field.create(
            id=uuid.uuid4(),
            name=f"Ділянка {index + 1:03d}",
            owner=rng.choice(OWNERS),
            crop=rng.choice(CROPS),
            geometry=_random_quad(
                ORIGIN_LAT + (row + 0.5) * CELL_DEG,
                ORIGIN_LON + (column + 0.5) * CELL_DEG,
                rng,
            ),
            created_at=datetime.now(UTC),
        )
        repository.save(field)
        fields.append(field)
    return fields


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample fields.")
    parser.add_argument("--count", type=int, default=100, help="number of fields")
    parser.add_argument("--seed", type=int, default=None, help="seed for reproducible output")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")

    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        fields = seed_fields(session, args.count, random.Random(args.seed))
        session.commit()

    sample = fields[0].geometry.centroid
    print(f"Seeded {len(fields)} fields.")
    print(
        "Try: curl 'http://localhost:8000/api/fields/find-by-point"
        f"?lat={sample.latitude:.6f}&lon={sample.longitude:.6f}'"
    )


if __name__ == "__main__":
    main()
