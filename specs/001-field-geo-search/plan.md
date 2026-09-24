# Implementation Plan: Agricultural Field Management & Point-Based Search

**Branch**: `001-field-geo-search` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-field-geo-search/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Deliver two capabilities: (1) create a `Field` with name, owner, crop, and a polygon boundary
that is validated as closed, non-self-intersecting, and ≥0.1 hectares; (2) search fields by a
point coordinate, returning every field whose boundary contains that point. Technical approach:
Clean Architecture per the project constitution — polygon validation (closed/simple/area) lives in
the domain layer using pure computational-geometry libraries (no DB round-trip required to reject
invalid input); persistence and spatial querying use PostgreSQL + PostGIS with a GIST index,
accessed only through an abstract repository interface; a FastAPI router exposes both operations.
The stakeholder-proposed Redis/geohash caching layer is deferred (see Complexity Tracking) — it is
not required to meet the spec's stated performance target and adds infrastructure not justified by
current scope.

## Technical Context

**Language/Version**: Python 3.12 (constitution mandates full type hints, mypy-compliant)

**Primary Dependencies**: FastAPI (presentation), Pydantic v2 (frozen domain value objects, DTOs),
SQLAlchemy 2.x + GeoAlchemy2 (infrastructure ORM), Shapely + pyproj (domain-layer geometry
validation — closed/simple/geodesic area, no DB dependency), Alembic (migrations)

**Storage**: PostgreSQL 16+ with the PostGIS extension; `geometry`/`geography` column with a GIST
index on the field boundary

**Testing**: pytest + pytest-asyncio for unit and integration tests; testcontainers-python to spin
up an isolated PostGIS instance per integration test run (per constitution Principle VIII — no
shared/dev database in tests)

**Target Platform**: Linux server, containerized (Docker Compose for local dev/CI parity)

**Project Type**: web-service (backend API)

**Performance Goals**: Point search returns results in under 1 second for a system with up to
10,000 fields (spec SC-003). A GIST-indexed PostGIS query meets this with wide margin without
additional caching.

**Constraints**: All validation failures raise explicit domain exceptions (constitution Principle
VII); domain layer has zero framework/ORM/HTTP dependencies (Principles I, V); application layer
depends only on the abstract `FieldRepository` interface (Principle VI).

**Scale/Scope**: Up to 10,000 fields (spec SC-003). No multi-tenant visibility filtering — search
is global across all fields regardless of owner (spec FR-010).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Domain-Centric Design | PASS | `domain/field/` contains only entities, value objects, exceptions, and the abstract repository — no ORM, HTTP, or framework imports. |
| II. Clean Architecture / Layered Boundaries | PASS | Dependency direction is domain ← application ← infrastructure/presentation throughout (see Project Structure). |
| III. Strict Type Hinting | PASS | All domain/application/infrastructure/presentation code uses full type hints; Pydantic v2 frozen models for value objects and DTOs; mypy run in CI. |
| IV. Immutability by Default | PASS | `Coordinate` and `Polygon` value objects are frozen; `Field` aggregate state changes (if any, e.g. future crop updates) occur only via explicit methods, not attribute mutation. |
| V. No Framework Contamination in Domain | PASS | GeoAlchemy2/SQLAlchemy confined to `infrastructure/field/`. Shapely/pyproj used inside `domain/` are pure computational-geometry libraries with no DB/HTTP/framework coupling, so this does not violate the principle's intent (ORM/HTTP/decorators). |
| VI. Repository Abstraction | PASS | `application/` depends only on the abstract `FieldRepository` defined in `domain/field/repository.py`; `PostgisFieldRepository` (concrete) lives in `infrastructure/field/`. |
| VII. Fail Fast with Explicit Errors | PASS | Distinct domain exceptions per rule: `PolygonNotClosedError`, `SelfIntersectingPolygonError`, `PolygonTooSmallError`, `MissingFieldAttributeError`, `InvalidCoordinateError`. |
| VIII. Test-First & Fixture Discipline | PASS | Domain unit tests run with no DB/framework at all; integration tests use testcontainers-provisioned, isolated PostGIS instances (no shared dev DB, no manual cleanup). |

**Result**: No unjustified violations. One item (Redis/geohash caching) from the stakeholder's
proposed plan is deferred rather than adopted — see Complexity Tracking for rationale.

## Project Structure

### Documentation (this feature)

```text
specs/001-field-geo-search/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── domain/
│   └── field/
│       ├── entities.py        # Field aggregate root
│       ├── value_objects.py   # Coordinate, Polygon (frozen; closed/simple/area validation)
│       ├── exceptions.py      # PolygonNotClosedError, SelfIntersectingPolygonError,
│       │                      # PolygonTooSmallError, MissingFieldAttributeError,
│       │                      # InvalidCoordinateError
│       └── repository.py      # Abstract FieldRepository interface
│
├── application/
│   └── field/
│       ├── create_field.py            # CreateFieldUseCase (command handler)
│       └── find_fields_by_point.py    # FindFieldsByPointUseCase (query handler)
│
├── infrastructure/
│   └── field/
│       ├── models.py              # SQLAlchemy + GeoAlchemy2 ORM model (geometry column, GIST index)
│       ├── mappers.py             # ORM record <-> domain Field entity translation
│       └── postgis_repository.py  # Concrete FieldRepository (PostGIS ST_Contains query)
│
└── presentation/
    └── api/
        ├── field_router.py    # FastAPI router: POST /fields, GET /fields/search
        └── schemas.py         # Request/response DTOs (Pydantic)

tests/
├── unit/
│   └── domain/field/           # Pure domain tests — no DB, no framework
├── integration/
│   └── infrastructure/field/   # testcontainers-backed PostGIS repository tests
└── contract/
    └── api/field/              # API request/response contract tests
```

**Structure Decision**: Single backend service laid out by DDD layer (`domain/`, `application/`,
`infrastructure/`, `presentation/`) as mandated by the project constitution, with a `field/`
submodule per layer for this feature. No separate frontend/mobile project exists yet, so the
"Option 1" single-project layout applies, adapted to the constitution's layer names instead of the
template's generic `models/services/cli/lib`.

## Complexity Tracking

> Items below are not constitution violations, but they depart from the stakeholder-proposed plan
> and are recorded here for visibility, per the general principle that complexity must be
> justified against actual requirements.

| Proposed Addition | Why Deferred | Simpler Alternative Adopted |
|---|---|---|
| Redis geohash cache-aside layer | No functional or success-criteria requirement in spec.md calls for it. SC-003 only requires <1s response at ≤10,000 fields, which a GIST-indexed PostGIS query satisfies by 1-2 orders of magnitude without a cache. Adding Redis introduces a second stateful service, cache-invalidation logic on every field create/update, and operational complexity with no measured need. | Rely on the PostGIS GIST spatial index alone for Phase 3. Revisit caching only if production load actually approaches or exceeds SC-003's bound and profiling shows the database is the bottleneck. |
| Sub-millisecond / <15ms p95 latency target | Not derived from spec.md; spec's only performance requirement is SC-003 (<1s @ ≤10,000 fields). Designing and benchmarking against an unwritten, much stricter target risks over-engineering the query/caching path. | Track SC-003 as the binding performance gate. The <15ms figure may be kept as an internal stretch/monitoring goal, but it is not a release gate for this feature. |
