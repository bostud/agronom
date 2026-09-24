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

VALID_BOUNDARY = Polygon(
    vertices=(
        Coordinate(latitude=50.4501, longitude=30.5234),
        Coordinate(latitude=50.4501, longitude=30.5250),
        Coordinate(latitude=50.4515, longitude=30.5250),
        Coordinate(latitude=50.4515, longitude=30.5234),
        Coordinate(latitude=50.4501, longitude=30.5234),
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


def test_save_persists_field_with_all_attributes_intact(
    session_factory: sessionmaker[Session],
) -> None:
    field = Field.create(
        id=uuid.uuid4(),
        name="North Forty",
        owner="Ivan Bondarenko",
        crop="wheat",
        geometry=VALID_BOUNDARY,
        created_at=datetime.now(UTC),
    )

    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        repository.save(field)
        session.commit()

    with session_factory() as session:
        repository = PostgisFieldRepository(session)
        [found] = repository.find_containing_point(
            Coordinate(latitude=50.4508, longitude=30.5242)
        )

    assert found.id == field.id
    assert found.name == field.name
    assert found.owner == field.owner
    assert found.crop == field.crop
    assert found.geometry.vertices[0] == field.geometry.vertices[0]
