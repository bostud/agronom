import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from src.domain.field.entities import Field
from src.domain.field.value_objects import Coordinate, Polygon
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


def _make_field(geometry: Polygon, name: str) -> Field:
    return Field.create(
        id=uuid.uuid4(),
        name=name,
        owner="Owner",
        crop="wheat",
        geometry=geometry,
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
def seeded_fields(session_factory: sessionmaker[Session]) -> dict[str, Field]:
    field_a = _make_field(_square(0.0, 0.0, 0.01), "Field A")
    field_b = _make_field(_square(0.005, 0.005, 0.01), "Field B (overlaps A)")

    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        repository.save(field_a)
        repository.save(field_b)
        session.commit()

    return {"a": field_a, "b": field_b}


def test_point_inside_one_field_returns_that_field(
    session_factory: sessionmaker[Session], seeded_fields: dict[str, Field]
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        results = repository.find_containing_point(
            Coordinate(latitude=0.001, longitude=0.001)
        )
    assert [f.id for f in results] == [seeded_fields["a"].id]


def test_point_inside_overlap_returns_both_fields(
    session_factory: sessionmaker[Session], seeded_fields: dict[str, Field]
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        results = repository.find_containing_point(
            Coordinate(latitude=0.007, longitude=0.007)
        )
    result_ids = {f.id for f in results}
    assert result_ids == {seeded_fields["a"].id, seeded_fields["b"].id}


def test_point_outside_all_fields_returns_empty_list(
    session_factory: sessionmaker[Session], seeded_fields: dict[str, Field]
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        results = repository.find_containing_point(
            Coordinate(latitude=45.0, longitude=45.0)
        )
    assert results == []


def test_point_on_boundary_edge_is_deterministic(
    session_factory: sessionmaker[Session], seeded_fields: dict[str, Field]
) -> None:
    edge_point = Coordinate(latitude=0.0, longitude=0.005)
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        first = repository.find_containing_point(edge_point)
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        second = repository.find_containing_point(edge_point)
    assert [f.id for f in first] == [f.id for f in second]
