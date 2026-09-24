---

description: "Task list template for feature implementation"
---

# Tasks: Agricultural Field Management & Point-Based Search

**Input**: Design documents from `/specs/001-field-geo-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/field-api.md, quickstart.md

**Tests**: Included. The project constitution (Principle VIII, "Test-First & Fixture Discipline")
mandates domain unit tests independent of any database/framework, plus integration tests using
isolated containers — these are binding governance requirements, not optional additions.

**Organization**: Tasks are grouped by user story (US1 = Register a New Field, US2 = Find Fields at
a Point) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Single backend service, laid out by DDD layer per plan.md:
`src/domain/`, `src/application/`, `src/infrastructure/`, `src/presentation/`, `tests/unit/`,
`tests/integration/`, `tests/contract/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory skeleton with `__init__.py` files: `src/domain/field/`,
      `src/application/field/`, `src/infrastructure/field/`, `src/presentation/api/`,
      `tests/unit/domain/field/`, `tests/integration/infrastructure/field/`,
      `tests/contract/api/field/`, per plan.md Project Structure.
- [X] T002 Initialize the Python project in `pyproject.toml` with dependencies: `fastapi`,
      `pydantic>=2`, `sqlalchemy>=2`, `geoalchemy2`, `shapely`, `pyproj`, `alembic`, `uvicorn`
      (plan.md Technical Context, research.md).
- [X] T003 [P] Configure mypy in strict mode (`pyproject.toml`/`mypy.ini`) so all function
      signatures and public attributes require complete type hints, per constitution Principle
      III ("Strict Type Hinting... mypy compliant").
- [X] T004 [P] Configure `pytest`, `pytest-asyncio`, and `testcontainers` as dev dependencies with
      test discovery config in `pyproject.toml`.
- [X] T005 [P] Create `docker-compose.yml` defining `web` (FastAPI app) and `db`
      (`postgis/postgis:16-3.4`) services (research.md Decision 6).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain primitives and persistence plumbing that BOTH user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 [P] Create domain exceptions in `src/domain/field/exceptions.py`: a `FieldDomainError`
      base class plus `InvalidCoordinateError`, `PolygonNotClosedError`,
      `SelfIntersectingPolygonError`, `PolygonTooSmallError`, `MissingFieldAttributeError`
      (data-model.md Domain Exceptions table).
- [X] T007 Create `Coordinate` and `Polygon` value objects in `src/domain/field/value_objects.py`
      (depends on T006): `Coordinate` is immutable with latitude required in the range -90.0 to
      90.0 and longitude required in the range -180.0 to 180.0, raising `InvalidCoordinateError`
      otherwise. `Polygon` is immutable, requires a minimum of 3 distinct vertices before closure,
      raises `PolygonNotClosedError` unless "its first and last points coincide" (FR-002), raises
      `SelfIntersectingPolygonError` when any two non-adjacent edges intersect (FR-003), and raises
      `PolygonTooSmallError` — with the computed area stated in the message — when the geodesic
      area is "smaller than 0.1 hectares" (FR-004), computed via `pyproj.Geod.geometry_area_perimeter`
      per research.md Decision 2.
- [X] T008 Create the `Field` aggregate root in `src/domain/field/entities.py` (depends on T007)
      with attributes `id` (UUID), `name` (str, required), `owner` (str, required), `crop` (str,
      required), `boundary` (Polygon, required), `created_at` (datetime); raises
      `MissingFieldAttributeError` naming the missing attribute(s) when "name, owner, crop, or
      geometry is missing" (FR-005).
- [X] T009 [P] Define the abstract `FieldRepository` interface in
      `src/domain/field/repository.py` with `save(field: Field) -> None` and
      `find_containing_point(point: Coordinate) -> list[Field]` (data-model.md Repository
      Interface) — no database logic in this file (constitution Principle I).
- [X] T010 Create the SQLAlchemy + GeoAlchemy2 ORM model with a GIST-indexed geometry column in
      `src/infrastructure/field/models.py` (depends on T008; research.md Decision 3).
- [X] T011 Create the Alembic migration provisioning the PostGIS extension, the `field` table, and
      its GIST index in `migrations/versions/` (depends on T010).
- [X] T012 Create the ORM-to-domain mapper in `src/infrastructure/field/mappers.py` (depends on
      T008, T010), translating between `Field`/`Polygon`/`Coordinate` and the ORM geometry column
      so no PostGIS/SQLAlchemy type crosses into `domain/` or `application/` (constitution
      Principles V, VI).

**Checkpoint**: Foundation ready — User Story 1 and User Story 2 implementation can now begin.

---

## Phase 3: User Story 1 - Register a New Field (Priority: P1) 🎯 MVP

**Goal**: Create a field with name, owner, crop, and geometry; reject any polygon that is not
closed, self-intersects, or encloses less than 0.1 hectares.

**Independent Test**: Submit a field with a name, owner, crop, and a valid closed,
non-self-intersecting polygon of ≥0.1 ha, and confirm it is saved and retrievable with all
attributes intact; submit each invalid variant and confirm rejection with no field created.

### Tests for User Story 1 ⚠️

> **Write these tests FIRST, ensure they FAIL before implementation**

- [X] T013 [US1] Unit test `Coordinate` and `Polygon` validation in
      `tests/unit/domain/field/test_value_objects.py` (depends on T007): valid closed polygon
      accepted; open polygon (first ≠ last point) rejected with `PolygonNotClosedError` (FR-002);
      self-intersecting polygon rejected with `SelfIntersectingPolygonError` (FR-003); polygon
      area below 0.1 hectares rejected with `PolygonTooSmallError` stating the computed area
      (FR-004); polygon with fewer than 3 distinct vertices rejected (Edge Case); coordinate with
      out-of-range latitude/longitude rejected with `InvalidCoordinateError`.
- [X] T014 [P] [US1] Unit test `Field` required-attribute validation in
      `tests/unit/domain/field/test_entities.py` (depends on T008): missing `name`, `owner`,
      `crop`, or `boundary` raises `MissingFieldAttributeError` naming the missing attribute(s)
      (FR-005).
- [X] T015 [P] [US1] Contract test `POST /fields` in
      `tests/contract/api/field/test_create_field.py` (per contracts/field-api.md): valid
      submission returns `201` with `area_ha >= 0.1`; each invalid case (not closed,
      self-intersecting, below 0.1ha, <3 vertices, missing attribute) returns `422` with the
      matching `detail` message from the contract's error table.
- [X] T016 [P] [US1] Integration test `PostgisFieldRepository.save` in
      `tests/integration/infrastructure/field/test_postgis_repository_save.py` using a
      testcontainers-provisioned isolated PostGIS instance (research.md Decision 5): a saved field
      is retrievable with `name`, `owner`, `crop`, and `boundary` intact.

### Implementation for User Story 1

- [X] T017 [US1] Implement `CreateFieldUseCase` in `src/application/field/create_field.py`
      (depends on T008, T009): accepts name/owner/crop/boundary, constructs the `Field` aggregate
      (domain validation raises on invalid input), and persists it via the injected abstract
      `FieldRepository` (dependency inversion, constitution Principle VI).
- [X] T018 [US1] Implement `PostgisFieldRepository.save` in
      `src/infrastructure/field/postgis_repository.py` (depends on T010, T011, T012): maps the
      `Field` aggregate to the ORM model via the mapper and persists it.
- [X] T019 [US1] Implement `CreateFieldRequest` and `FieldResponse` Pydantic DTOs in
      `src/presentation/api/schemas.py` matching the `POST /fields` request/response shapes in
      contracts/field-api.md.
- [X] T020 [US1] Implement the `POST /fields` endpoint in
      `src/presentation/api/field_router.py` (depends on T017, T019): invokes `CreateFieldUseCase`
      and maps `PolygonNotClosedError`, `SelfIntersectingPolygonError`, `PolygonTooSmallError`, and
      `MissingFieldAttributeError` to `422` responses with the exact `detail` messages defined in
      contracts/field-api.md.
- [X] T021 [US1] Wire FastAPI dependency providers for `CreateFieldUseCase` and
      `PostgisFieldRepository` in `src/presentation/api/dependencies.py` (depends on T017, T018).

**Checkpoint**: User Story 1 is fully functional and testable independently — fields can be
created via the API with all validation rules enforced end to end.

---

## Phase 4: User Story 2 - Find Fields at a Point (Priority: P2)

**Goal**: Given a point coordinate, return every field whose boundary contains that point.

**Independent Test**: Create one or more fields with known boundaries; search a coordinate known
to fall inside one field's boundary and confirm that exact field is returned; search a coordinate
outside all boundaries and confirm an empty result.

### Tests for User Story 2 ⚠️

- [X] T022 [P] [US2] Contract test `GET /fields/search` in
      `tests/contract/api/field/test_search_fields.py` (per contracts/field-api.md): point inside
      a field's boundary returns `200` with that field (FR-007); point outside every boundary
      returns `200` with an empty `fields` list, not an error (FR-008); malformed or out-of-range
      `lat`/`lon` returns `422` (FR-009).
- [X] T023 [P] [US2] Integration test `PostgisFieldRepository.find_containing_point` in
      `tests/integration/infrastructure/field/test_postgis_repository_search.py` using a
      testcontainers-provisioned isolated PostGIS instance: a point inside one field; a point
      inside two overlapping fields (both returned, Acceptance Scenario 3); a point outside all
      fields (empty list); a point exactly on a boundary edge (same input always yields the same
      result, Acceptance Scenario 4).

### Implementation for User Story 2

- [X] T024 [US2] Implement `FindFieldsByPointUseCase` in
      `src/application/field/find_fields_by_point.py` (depends on T007, T009): constructs a
      `Coordinate` from the input (raising `InvalidCoordinateError` on malformed/out-of-range
      input per FR-009) and returns the result of `FieldRepository.find_containing_point`, which
      may be an empty list (FR-008).
- [X] T025 [US2] Implement `PostgisFieldRepository.find_containing_point` in
      `src/infrastructure/field/postgis_repository.py` (depends on T010, T012, T018): queries
      using an indexed `ST_Contains`/`ST_Within` check, optionally pre-filtered with the `&&`
      bounding-box operator (research.md Decision 3), and maps results back to domain `Field`
      entities via the mapper.
- [X] T026 [US2] Implement the `FieldSearchResponse` Pydantic DTO in
      `src/presentation/api/schemas.py` (depends on T019) matching the `GET /fields/search`
      response shape in contracts/field-api.md.
- [X] T027 [US2] Implement the `GET /fields/search` endpoint in
      `src/presentation/api/field_router.py` (depends on T020, T024, T026): parses `lat`/`lon`
      query parameters, invokes `FindFieldsByPointUseCase`, maps `InvalidCoordinateError` to a
      `422` response, and returns `200` with the (possibly empty) `fields` list.

**Checkpoint**: User Story 1 and User Story 2 both work independently and together.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T028 [P] Run all quickstart.md scenarios (1–5) end-to-end against the docker-compose
      environment and confirm each matches its documented expected outcome.
- [X] T029 [P] Run `mypy` across `src/` in strict mode and resolve any typing errors (constitution
      Principle III).
- [X] T030 Audit `src/domain/field/` to confirm zero imports from `application/`,
      `infrastructure/`, `presentation/`, or any ORM/HTTP/framework module (constitution
      Principles I, II, V).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion only.
- **User Story 2 (Phase 4)**: Depends on Foundational completion; shares
  `src/infrastructure/field/postgis_repository.py` and
  `src/presentation/api/field_router.py`/`schemas.py` with User Story 1 (T025–T027 extend files
  T018/T019/T020 create), so in practice US2 implementation tasks follow US1's corresponding
  tasks even though the story is conceptually independent.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### Within Each User Story

- Tests (T013–T016, T022–T023) MUST be written and FAIL before their corresponding implementation
  tasks.
- Value objects (T007) before entities (T008) before use cases (T017, T024) before endpoints
  (T020, T027).
- Repository interface (T009) before use cases; concrete repository (T010–T012) before repository
  method implementations (T018, T025).

### Parallel Opportunities

- Setup tasks T003, T004, T005 can run in parallel (different files).
- Foundational tasks T006 and T009 can run in parallel (different files, no dependency between
  them).
- Within US1: T014, T015, T016 can run in parallel with each other and with T013 (different
  files).
- Within US2: T022 and T023 can run in parallel (different files).
- Polish tasks T028 and T029 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch these tests for User Story 1 together:
Task: "Unit test Field required-attribute validation in tests/unit/domain/field/test_entities.py"
Task: "Contract test POST /fields in tests/contract/api/field/test_create_field.py"
Task: "Integration test PostgisFieldRepository.save in tests/integration/infrastructure/field/test_postgis_repository_save.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run T013–T016 and quickstart.md Scenarios 1–2 independently.
5. Deploy/demo if ready — field creation with full validation is a usable increment on its own.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. Add User Story 1 → validate independently → deploy/demo (MVP).
3. Add User Story 2 → validate independently (quickstart Scenarios 3–5) → deploy/demo.
4. Polish (Phase 5) once both stories are complete.
