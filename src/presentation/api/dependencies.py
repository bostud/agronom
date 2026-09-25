from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.application.field.create_field import CreateFieldUseCase
from src.application.field.find_fields_by_point import FindFieldsByPointUseCase
from src.application.field.get_field_by_id import GetFieldByIdUseCase
from src.application.field.list_fields import ListFieldsUseCase
from src.domain.field.repository import FieldRepository
from src.infrastructure.field.postgis_repository import PostgisFieldRepository
from src.settings import DATABASE_URL

_engine = create_engine(DATABASE_URL)
_SessionLocal = sessionmaker(bind=_engine)


def get_session() -> Iterator[Session]:
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_field_repository(session: Session = Depends(get_session)) -> FieldRepository:
    return PostgisFieldRepository(session)


def get_create_field_use_case(
    repository: FieldRepository = Depends(get_field_repository),
) -> CreateFieldUseCase:
    return CreateFieldUseCase(repository)


def get_find_fields_by_point_use_case(
    repository: FieldRepository = Depends(get_field_repository),
) -> FindFieldsByPointUseCase:
    return FindFieldsByPointUseCase(repository)


def get_list_fields_use_case(
    repository: FieldRepository = Depends(get_field_repository),
) -> ListFieldsUseCase:
    return ListFieldsUseCase(repository)


def get_get_field_by_id_use_case(
    repository: FieldRepository = Depends(get_field_repository),
) -> GetFieldByIdUseCase:
    return GetFieldByIdUseCase(repository)
