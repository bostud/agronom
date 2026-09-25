"""Seed the database with realistic test fields located in Ukraine.

Generates fields of varied size and shape clustered around agricultural regions,
with a mix of crops and owners. Some fields deliberately overlap:

* "hotspots" - a point shared by 2-5 fields (partial overlaps and nested fields),
  handy for testing multiple matches in ``GET /api/fields/find-by-point``;
* neighbour overlaps - a field shifted onto an already generated one.

Every field goes through the domain model, so the same validation rules apply as
for ``POST /api/fields``.

Usage:
    python -m scripts.seed_fields                       # 1000 fields, seed 42
    python -m scripts.seed_fields --count 5000 --clear  # wipe table, then seed
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from shapely import STRtree
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon as ShapelyPolygon
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from src.domain.field.entities import Field
from src.domain.field.exceptions import FieldDomainError
from src.domain.field.value_objects import Coordinate, Polygon
from src.infrastructure.field.models import FieldModel
from src.infrastructure.field.postgis_repository import PostgisFieldRepository
from src.settings import DATABASE_URL

METERS_PER_DEGREE_LAT = 111_320.0
COORDINATE_PRECISION = 7
MAX_ATTEMPTS = 50


@dataclass(frozen=True)
class Region:
    name: str
    latitude: float
    longitude: float
    spread_deg: float


# Agricultural areas of Ukraine; fields are scattered around each center.
REGIONS: tuple[Region, ...] = (
    Region("Київська", 50.08, 29.92, 0.25),
    Region("Житомирська", 49.90, 28.60, 0.25),
    Region("Вінницька", 49.10, 28.80, 0.30),
    Region("Хмельницька", 49.42, 26.98, 0.25),
    Region("Тернопільська", 49.55, 25.59, 0.20),
    Region("Львівська", 49.95, 24.60, 0.15),
    Region("Черкаська", 49.10, 30.95, 0.25),
    Region("Кіровоградська", 48.51, 32.26, 0.30),
    Region("Полтавська", 49.59, 34.55, 0.30),
    Region("Харківська", 49.37, 35.45, 0.20),
    Region("Сумська", 50.75, 33.47, 0.20),
    Region("Чернігівська", 50.59, 32.39, 0.25),
    Region("Дніпропетровська", 48.20, 34.60, 0.25),
    Region("Миколаївська", 47.69, 32.51, 0.20),
    Region("Одеська", 47.94, 29.62, 0.20),
)

# (crop, weight) - roughly follows the Ukrainian sowing structure.
CROPS: tuple[tuple[str, int], ...] = (
    ("wheat", 25),
    ("corn", 20),
    ("sunflower", 20),
    ("barley", 8),
    ("rapeseed", 7),
    ("soybean", 7),
    ("sugar beet", 3),
    ("peas", 3),
    ("rye", 2),
    ("oats", 2),
    ("buckwheat", 2),
    ("potato", 1),
)

COMPANIES: tuple[str, ...] = (
    "ТОВ «Агро-Світанок»",
    "ТОВ «Золотий Колос»",
    "ТОВ «Степ Агро»",
    "СТОВ «Дружба»",
    "ПП «Нива Поділля»",
    "ТОВ «Полтавська нива»",
    "ФГ «Чорнозем»",
    "ФГ «Лан»",
)

FIRST_NAMES: tuple[str, ...] = (
    "Іван", "Петро", "Олена", "Марія", "Андрій", "Оксана", "Тарас", "Василь",
    "Наталія", "Микола", "Світлана", "Олександр", "Юлія", "Сергій", "Галина",
)

LAST_NAMES: tuple[str, ...] = (
    "Бондаренко", "Коваленко", "Шевченко", "Мельник", "Ткаченко", "Кравченко",
    "Олійник", "Савченко", "Іваненко", "Руденко", "Мороз", "Поліщук", "Лисенко",
    "Гончаренко", "Марченко", "Козак", "Литвиненко", "Павленко",
)

FIELD_NAME_PREFIXES: tuple[str, ...] = (
    "Північне", "Південне", "Східне", "Західне", "Нижнє", "Верхнє", "Біля ставу",
    "За лісосмугою", "Біля траси", "Балка", "Толока", "Кругле", "Довге", "Клин",
)

# (min_ha, max_ha, weight) - private plots, farm fields, large and huge fields.
SIZE_BUCKETS: tuple[tuple[float, float, int], ...] = (
    (0.5, 10.0, 25),
    (10.0, 100.0, 50),
    (100.0, 400.0, 20),
    (400.0, 1500.0, 5),
)


@dataclass(frozen=True)
class GeneratedField:
    field: Field
    region: str
    shape: ShapelyPolygon


@dataclass(frozen=True)
class Hotspot:
    latitude: float
    longitude: float
    region: str


class FieldGenerator:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._owners = self._build_owner_pool()
        self._now = datetime.now(UTC)

    def random_region(self) -> Region:
        return self._rng.choice(REGIONS)

    def random_center(self, region: Region) -> tuple[float, float]:
        latitude = self._rng.gauss(region.latitude, region.spread_deg / 2)
        longitude = self._rng.gauss(region.longitude, region.spread_deg)
        return latitude, longitude

    def random_area_ha(self) -> float:
        low, high, _weight = self._rng.choices(
            SIZE_BUCKETS, weights=[bucket[2] for bucket in SIZE_BUCKETS]
        )[0]
        return math.exp(self._rng.uniform(math.log(low), math.log(high)))

    def make_field(
        self,
        region: Region,
        center: tuple[float, float],
        area_ha: float,
        must_contain: tuple[float, float] | None = None,
        must_intersect: ShapelyPolygon | None = None,
    ) -> GeneratedField | None:
        """Build a valid field around ``center``, retrying the shape until constraints hold."""
        for _ in range(MAX_ATTEMPTS):
            polygon = self._make_polygon(center, area_ha)
            if polygon is None:
                continue
            shape = ShapelyPolygon([(c.longitude, c.latitude) for c in polygon.vertices])
            if must_contain is not None and not shape.contains(
                ShapelyPoint(must_contain[1], must_contain[0])
            ):
                continue
            if must_intersect is not None and shape.intersection(must_intersect).area == 0:
                continue
            field = Field.create(
                id=uuid.UUID(int=self._rng.getrandbits(128), version=4),
                name=self._random_field_name(),
                owner=self._random_owner(),
                crop=self._random_crop(),
                geometry=polygon,
                created_at=self._now - timedelta(minutes=self._rng.randint(0, 2 * 365 * 24 * 60)),
            )
            return GeneratedField(field=field, region=region.name, shape=shape)
        return None

    def _make_polygon(self, center: tuple[float, float], area_ha: float) -> Polygon | None:
        outline = self._rng.choices(
            (self._rectangle, self._trapezoid, self._irregular, self._l_shape),
            weights=(45, 20, 25, 10),
        )[0]()
        scale = math.sqrt(area_ha * 10_000 / _shoelace_area(outline))
        rotation = self._rng.uniform(0, math.pi)
        cos_r, sin_r = math.cos(rotation), math.sin(rotation)

        latitude0, longitude0 = center
        meters_per_degree_lon = METERS_PER_DEGREE_LAT * math.cos(math.radians(latitude0))
        vertices = [
            Coordinate(
                latitude=round(latitude0 + (x * sin_r + y * cos_r) * scale / METERS_PER_DEGREE_LAT, COORDINATE_PRECISION),
                longitude=round(longitude0 + (x * cos_r - y * sin_r) * scale / meters_per_degree_lon, COORDINATE_PRECISION),
            )
            for x, y in outline
        ]
        try:
            return Polygon(vertices=(*vertices, vertices[0]))
        except (FieldDomainError, ValueError):
            return None

    # Outlines are unit-ish shapes around the origin, open rings, counter-clockwise.

    def _rectangle(self) -> list[tuple[float, float]]:
        aspect = self._rng.uniform(1.0, 4.0)
        w, h = aspect / 2, 0.5
        return [(-w, -h), (w, -h), (w, h), (-w, h)]

    def _trapezoid(self) -> list[tuple[float, float]]:
        w, h = self._rng.uniform(0.5, 1.5), 0.5
        top_left = self._rng.uniform(0.0, 0.4) * w
        top_right = self._rng.uniform(0.0, 0.4) * w
        return [(-w, -h), (w, -h), (w - top_right, h), (-w + top_left, h)]

    def _irregular(self) -> list[tuple[float, float]]:
        """Star-shaped polygon: sorted angles around the origin keep it simple."""
        count = self._rng.randint(5, 9)
        step = 2 * math.pi / count
        return [
            (radius * math.cos(angle), radius * math.sin(angle))
            for angle, radius in (
                (i * step + self._rng.uniform(-0.3, 0.3) * step, self._rng.uniform(0.7, 1.0))
                for i in range(count)
            )
        ]

    def _l_shape(self) -> list[tuple[float, float]]:
        s, t = self._rng.uniform(0.3, 0.7), self._rng.uniform(0.3, 0.7)
        points = [(0.0, 0.0), (1.0, 0.0), (1.0, t), (s, t), (s, 1.0), (0.0, 1.0)]
        # Shift so the origin sits inside the corner block of the L.
        return [(x - s / 2, y - t / 2) for x, y in points]

    def _random_crop(self) -> str:
        return self._rng.choices([c for c, _ in CROPS], weights=[w for _, w in CROPS])[0]

    def _random_owner(self) -> str:
        # Companies own many fields each, individual farmers a few.
        if self._rng.random() < 0.4:
            return self._rng.choice(COMPANIES)
        return self._rng.choice(self._owners)

    def _random_field_name(self) -> str:
        return f"{self._rng.choice(FIELD_NAME_PREFIXES)} №{self._rng.randint(1, 250)}"

    def _build_owner_pool(self) -> list[str]:
        farmers = {
            f"ФГ {self._rng.choice(LAST_NAMES)} {self._rng.choice(FIRST_NAMES)}"
            for _ in range(60)
        }
        return sorted(farmers)


def _shoelace_area(points: list[tuple[float, float]]) -> float:
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
        )
    ) / 2


def generate(
    count: int, hotspot_count: int, overlap_ratio: float, rng: random.Random
) -> tuple[list[GeneratedField], list[Hotspot]]:
    generator = FieldGenerator(rng)
    fields: list[GeneratedField] = []
    hotspots: list[Hotspot] = []

    # 1. Hotspots: several fields sharing one point (partial overlaps and nested fields).
    for _ in range(hotspot_count):
        if len(fields) >= count:
            break
        region = generator.random_region()
        point = generator.random_center(region)
        members = rng.randint(2, 5)
        for _ in range(min(members, count - len(fields))):
            area_ha = generator.random_area_ha()
            max_offset_m = math.sqrt(area_ha * 10_000) * 0.3
            center = _offset(point, rng.uniform(0, max_offset_m), rng.uniform(0, 2 * math.pi))
            generated = generator.make_field(region, center, area_ha, must_contain=point)
            if generated is not None:
                fields.append(generated)
        hotspots.append(Hotspot(latitude=point[0], longitude=point[1], region=region.name))

    # 2. Regular fields; a share of them is shifted onto an existing field.
    while len(fields) < count:
        area_ha = generator.random_area_ha()
        if fields and rng.random() < overlap_ratio:
            base = rng.choice(fields)
            base_radius_m = math.sqrt(base.field.area_ha * 10_000) / 2
            base_center = base.field.geometry.centroid
            center = _offset(
                (base_center.latitude, base_center.longitude),
                rng.uniform(0.3, 1.0) * base_radius_m,
                rng.uniform(0, 2 * math.pi),
            )
            region = next(r for r in REGIONS if r.name == base.region)
            generated = generator.make_field(region, center, area_ha, must_intersect=base.shape)
        else:
            region = generator.random_region()
            generated = generator.make_field(region, generator.random_center(region), area_ha)
        if generated is not None:
            fields.append(generated)

    return fields, hotspots


def _offset(point: tuple[float, float], distance_m: float, bearing: float) -> tuple[float, float]:
    latitude, longitude = point
    d_lat = distance_m * math.cos(bearing) / METERS_PER_DEGREE_LAT
    d_lon = distance_m * math.sin(bearing) / (
        METERS_PER_DEGREE_LAT * math.cos(math.radians(latitude))
    )
    return latitude + d_lat, longitude + d_lon


def persist(fields: list[GeneratedField], database_url: str, clear: bool) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        if clear:
            deleted = session.execute(select(func.count()).select_from(FieldModel)).scalar_one()
            session.execute(delete(FieldModel))
            print(f"Видалено існуючих полів: {deleted}")
        repository = PostgisFieldRepository(session)
        for generated in fields:
            repository.save(generated.field)
    engine.dispose()


def print_summary(fields: list[GeneratedField], hotspots: list[Hotspot]) -> None:
    shapes = [generated.shape for generated in fields]
    tree = STRtree(shapes)
    left, right = tree.query(shapes, predicate="intersects")
    # Drop self-matches, duplicates and fields that merely share a border.
    pairs = [
        (i, j)
        for i, j in zip(left.tolist(), right.tolist())
        if i < j and not shapes[i].touches(shapes[j])
    ]
    overlapping_pairs = len(pairs)
    fields_with_overlap = len({index for pair in pairs for index in pair})

    areas = sorted(generated.field.area_ha for generated in fields)
    print(f"\nЗгенеровано полів: {len(fields)}")
    print(
        f"Площа, га: min {areas[0]:.2f}, медіана {areas[len(areas) // 2]:.2f}, "
        f"max {areas[-1]:.2f}, сумарно {sum(areas):,.0f}"
    )
    print(f"Власників: {len({g.field.owner for g in fields})}")
    print(f"Перекриваються: {fields_with_overlap} полів, {overlapping_pairs} пар")

    print("\nКультури:")
    for crop, total in Counter(g.field.crop for g in fields).most_common():
        print(f"  {crop:<12} {total}")

    print("\nРегіони:")
    for region, total in Counter(g.region for g in fields).most_common():
        print(f"  {region:<18} {total}")

    print("\nТочки з кількома збігами (для GET /api/fields/find-by-point):")
    for hotspot in hotspots[:10]:
        point = ShapelyPoint(hotspot.longitude, hotspot.latitude)
        matches = sum(1 for shape in shapes if shape.contains(point))
        print(
            f"  lat={hotspot.latitude:.6f}&lon={hotspot.longitude:.6f}"
            f"  -> полів: {matches} ({hotspot.region})"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--count", type=int, default=1000, help="кількість полів (default: 1000)")
    parser.add_argument("--seed", type=int, default=42, help="seed для відтворюваності")
    parser.add_argument(
        "--hotspots", type=int, default=30, help="кількість точок з кількома полями"
    )
    parser.add_argument(
        "--overlap-ratio",
        type=float,
        default=0.1,
        help="частка звичайних полів, зсунутих на вже існуюче поле (0..1)",
    )
    parser.add_argument("--clear", action="store_true", help="видалити всі поля перед сидінгом")
    parser.add_argument("--dry-run", action="store_true", help="лише згенерувати, без запису в БД")
    parser.add_argument("--database-url", default=DATABASE_URL)
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be positive")
    if not 0 <= args.overlap_ratio <= 1:
        parser.error("--overlap-ratio must be within [0, 1]")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    rng = random.Random(args.seed)
    fields, hotspots = generate(args.count, args.hotspots, args.overlap_ratio, rng)
    if not args.dry_run:
        persist(fields, args.database_url, args.clear)
    print_summary(fields, hotspots)


if __name__ == "__main__":
    main()
