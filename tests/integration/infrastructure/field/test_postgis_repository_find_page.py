import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from src.domain.common.pagination import PageRequest
from src.domain.field.entities import Field
from src.domain.field.value_objects import Coordinate, FieldFilter, Polygon
from src.infrastructure.field.models import Base
from src.infrastructure.field.postgis_repository import PostgisFieldRepository


def _square(min_lat: float, min_lon: float, side: float) -> Polygon:
    return Polygon(
        vertices=(
            Coordinate(latitude=min_lat, longitude=min_lon),
            Coordinate(latitude=min_lat, longitude=min_lon + side),
            Coordinate(latitude=min_lat + side, longitude=min_lon + side),
            Coordinate(latitude=min_lat + side, longitude=min_lon),
            Coordinate(latitude=min_lat, longitude=min_lon),
        )
    )


def _make_field(index: int, crop: str = "wheat", owner: str = "Owner") -> Field:
    return Field.create(
        id=uuid.uuid4(),
        name=f"Field {index}",
        owner=owner,
        crop=crop,
        geometry=_square(index * 0.02, 0.0, 0.01),
        created_at=datetime.now(UTC),
    )


@pytest.fixture(scope="module")
def session_factory() -> Iterator[sessionmaker[Session]]:
    with PostgresContainer("postgis/postgis:16-3.4", driver="psycopg") as postgres:
        engine = create_engine(postgres.get_connection_url())
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
        Base.metadata.create_all(engine)
        yield sessionmaker(bind=engine)


@pytest.fixture(scope="module")
def seeded(session_factory: sessionmaker[Session]) -> int:
    total = 25
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        for i in range(total):
            repository.save(_make_field(i))
        session.commit()
    return total


def test_find_page_returns_correct_first_page(
    session_factory: sessionmaker[Session], seeded: int
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        page = repository.find_page(FieldFilter(), PageRequest(limit=10, offset=0))

    assert len(page.items) == 10
    assert page.limit == 10
    assert page.offset == 0
    assert page.total == seeded


def test_find_page_consecutive_windows_are_disjoint(
    session_factory: sessionmaker[Session], seeded: int
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        first = repository.find_page(FieldFilter(), PageRequest(limit=10, offset=0))
        second = repository.find_page(FieldFilter(), PageRequest(limit=10, offset=10))

    ids_first = {f.id for f in first.items}
    ids_second = {f.id for f in second.items}
    assert len(second.items) == 10
    assert ids_first.isdisjoint(ids_second)


def test_find_page_supports_offsets_not_aligned_to_limit(
    session_factory: sessionmaker[Session], seeded: int
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        everything = repository.find_page(FieldFilter(), PageRequest(limit=100, offset=0))
        window = repository.find_page(FieldFilter(), PageRequest(limit=5, offset=7))

    assert [f.id for f in window.items] == [f.id for f in everything.items[7:12]]
    assert window.total == seeded


def test_find_page_partial_tail_and_offset_past_end(
    session_factory: sessionmaker[Session], seeded: int
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        tail = repository.find_page(FieldFilter(), PageRequest(limit=10, offset=20))
        beyond = repository.find_page(FieldFilter(), PageRequest(limit=10, offset=1000))

    assert len(tail.items) == 5  # 25 items, offset 20 -> 5 remain
    assert beyond.items == ()
    assert beyond.total == seeded


@pytest.fixture(scope="module")
def crop_owner_fields(session_factory: sessionmaker[Session]) -> dict[str, Field]:
    wheat_ivan = Field.create(
        id=uuid.uuid4(),
        name="Wheat-Ivan",
        owner="Ivan Bondarenko",
        crop="wheat",
        geometry=_square(50.0, 0.0, 0.01),
        created_at=datetime.now(UTC),
    )
    wheat_olena = Field.create(
        id=uuid.uuid4(),
        name="Wheat-Olena",
        owner="Olena Petrenko",
        crop="wheat",
        geometry=_square(50.02, 0.0, 0.01),
        created_at=datetime.now(UTC),
    )
    barley_ivan = Field.create(
        id=uuid.uuid4(),
        name="Barley-Ivan",
        owner="Ivan Bondarenko",
        crop="barley",
        geometry=_square(50.04, 0.0, 0.01),
        created_at=datetime.now(UTC),
    )
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        for field in (wheat_ivan, wheat_olena, barley_ivan):
            repository.save(field)
        session.commit()
    return {"wheat_ivan": wheat_ivan, "wheat_olena": wheat_olena, "barley_ivan": barley_ivan}


def test_find_page_filters_by_crop_case_insensitively(
    session_factory: sessionmaker[Session], crop_owner_fields: dict[str, Field]
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        page = repository.find_page(
            FieldFilter(crop="WHEAT"), PageRequest(limit=50, offset=0)
        )
    result_ids = {f.id for f in page.items}
    assert crop_owner_fields["wheat_ivan"].id in result_ids
    assert crop_owner_fields["wheat_olena"].id in result_ids
    assert crop_owner_fields["barley_ivan"].id not in result_ids


def test_find_page_filters_by_owner_substring_case_insensitively(
    session_factory: sessionmaker[Session], crop_owner_fields: dict[str, Field]
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        page = repository.find_page(
            FieldFilter(owner="ivan"), PageRequest(limit=50, offset=0)
        )
    result_ids = {f.id for f in page.items}
    assert crop_owner_fields["wheat_ivan"].id in result_ids
    assert crop_owner_fields["barley_ivan"].id in result_ids
    assert crop_owner_fields["wheat_olena"].id not in result_ids


def test_find_page_filters_by_crop_and_owner_combined(
    session_factory: sessionmaker[Session], crop_owner_fields: dict[str, Field]
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        page = repository.find_page(
            FieldFilter(crop="wheat", owner="ivan"), PageRequest(limit=50, offset=0)
        )
    result_ids = {f.id for f in page.items}
    assert result_ids == {crop_owner_fields["wheat_ivan"].id}


@pytest.fixture(scope="module")
def area_range_fields(session_factory: sessionmaker[Session]) -> dict[str, Field]:
    small = Field.create(
        id=uuid.uuid4(),
        name="Small",
        owner="Area Owner",
        crop="area-test-crop",
        geometry=_square(60.0, 0.0, 0.0015),
        created_at=datetime.now(UTC),
    )
    medium = Field.create(
        id=uuid.uuid4(),
        name="Medium",
        owner="Area Owner",
        crop="area-test-crop",
        geometry=_square(60.02, 0.0, 0.003),
        created_at=datetime.now(UTC),
    )
    large = Field.create(
        id=uuid.uuid4(),
        name="Large",
        owner="Area Owner",
        crop="area-test-crop",
        geometry=_square(60.05, 0.0, 0.006),
        created_at=datetime.now(UTC),
    )
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        for field in (small, medium, large):
            repository.save(field)
        session.commit()
    return {"small": small, "medium": medium, "large": large}


def test_find_page_filters_by_min_area_inclusive(
    session_factory: sessionmaker[Session], area_range_fields: dict[str, Field]
) -> None:
    min_area = area_range_fields["medium"].area_ha
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        page = repository.find_page(
            FieldFilter(crop="area-test-crop", min_area_ha=min_area),
            PageRequest(limit=50, offset=0),
        )
    result_ids = {f.id for f in page.items}
    assert result_ids == {area_range_fields["medium"].id, area_range_fields["large"].id}


def test_find_page_filters_by_max_area_inclusive(
    session_factory: sessionmaker[Session], area_range_fields: dict[str, Field]
) -> None:
    max_area = area_range_fields["medium"].area_ha
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        page = repository.find_page(
            FieldFilter(crop="area-test-crop", max_area_ha=max_area),
            PageRequest(limit=50, offset=0),
        )
    result_ids = {f.id for f in page.items}
    assert result_ids == {area_range_fields["small"].id, area_range_fields["medium"].id}


def test_find_page_filters_by_area_range_both_bounds(
    session_factory: sessionmaker[Session], area_range_fields: dict[str, Field]
) -> None:
    exact_area = area_range_fields["medium"].area_ha
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        page = repository.find_page(
            FieldFilter(
                crop="area-test-crop", min_area_ha=exact_area, max_area_ha=exact_area
            ),
            PageRequest(limit=50, offset=0),
        )
    result_ids = {f.id for f in page.items}
    assert result_ids == {area_range_fields["medium"].id}


def test_find_page_orders_duplicate_names_by_id(
    session_factory: sessionmaker[Session],
) -> None:
    crop = "tiebreak-crop"
    duplicates = [
        Field.create(
            id=uuid.uuid4(),
            name="Same Name",
            owner="Tie Owner",
            crop=crop,
            geometry=_square(70.0 + i * 0.02, 0.0, 0.01),
            created_at=datetime.now(UTC),
        )
        for i in range(6)
    ]
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        for field in duplicates:
            repository.save(field)
        session.commit()

    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        windows = [
            repository.find_page(FieldFilter(crop=crop), PageRequest(limit=2, offset=o))
            for o in (0, 2, 4)
        ]

    paged_ids = [f.id for w in windows for f in w.items]
    assert paged_ids == sorted((f.id for f in duplicates), key=str)
