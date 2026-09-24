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

VALID_GEOMETRY = Polygon(
    vertices=(
        Coordinate(latitude=70.0, longitude=0.0),
        Coordinate(latitude=70.0, longitude=0.01),
        Coordinate(latitude=70.01, longitude=0.01),
        Coordinate(latitude=70.01, longitude=0.0),
        Coordinate(latitude=70.0, longitude=0.0),
    )
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
def seeded_field(session_factory: sessionmaker[Session]) -> Field:
    field = Field.create(
        id=uuid.uuid4(),
        name="Findable Field",
        owner="Ivan Bondarenko",
        crop="wheat",
        geometry=VALID_GEOMETRY,
        created_at=datetime.now(UTC),
    )
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        repository.save(field)
        session.commit()
    return field


def test_find_by_id_returns_matching_field(
    session_factory: sessionmaker[Session], seeded_field: Field
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        found = repository.find_by_id(seeded_field.id)

    assert found is not None
    assert found.id == seeded_field.id
    assert found.name == seeded_field.name
    assert found.owner == seeded_field.owner
    assert found.crop == seeded_field.crop
    assert found.geometry == seeded_field.geometry
    assert found.created_at == seeded_field.created_at
    assert found.area_ha == pytest.approx(seeded_field.area_ha)


def test_find_by_id_round_trips_unicode_attributes(
    session_factory: sessionmaker[Session],
) -> None:
    field = Field.create(
        id=uuid.uuid4(),
        name="Поле Північне",
        owner="Іван Бондаренко",
        crop="пшениця озима",
        geometry=VALID_GEOMETRY,
        created_at=datetime.now(UTC),
    )
    with session_factory() as session:
        PostgisFieldRepository(session).save(field)
        session.commit()

    with session_factory() as session:
        found = PostgisFieldRepository(session).find_by_id(field.id)

    assert found is not None
    assert (found.name, found.owner, found.crop) == (
        "Поле Північне",
        "Іван Бондаренко",
        "пшениця озима",
    )


def test_find_by_id_returns_none_for_unknown_id(
    session_factory: sessionmaker[Session], seeded_field: Field
) -> None:
    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        found = repository.find_by_id(uuid.uuid4())

    assert found is None
