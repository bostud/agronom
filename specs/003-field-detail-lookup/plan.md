# Implementation Plan: Retrieve a Specific Field

**Branch**: `003-field-detail-lookup` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-field-detail-lookup/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Add a single-resource retrieval endpoint for the existing `Field` aggregate (from
`001-field-geo-search`): given a field's identifier, return its full details, or a clear
"not found" result if no field with that identifier exists. Technical approach: extend the
existing `FieldRepository` interface with `find_by_id`; add a `FieldNotFoundError` domain
exception, raised by a new `GetFieldByIdUseCase` when the repository returns nothing; expose
`GET /fields/{field_id}`. Malformed-identifier rejection (FR-004) is handled by the existing UUID
path-parameter type coercion at the presentation boundary — it is a request-format check, not a
business rule, so it needs no new domain exception. No new external dependencies or services.

## Technical Context

**Language/Version**: Python 3.12 (unchanged from `001-field-geo-search`)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x + GeoAlchemy2 — all already present
from `001-field-geo-search`; no new libraries required.

**Storage**: The existing PostgreSQL 16+/PostGIS `field` table from `001-field-geo-search`. No
schema change — this feature only reads by primary key.

**Testing**: pytest + pytest-asyncio + testcontainers-python (unchanged).

**Target Platform**: Linux server, containerized (unchanged).

**Project Type**: web-service (extension of the existing backend).

**Performance Goals**: Retrieval of an existing field completes in under 1 second (spec SC-001) —
trivially satisfied by a primary-key lookup.

**Constraints**: A non-existent identifier MUST yield a distinct "not found" result, never an
error or an empty-but-successful payload (FR-003); a malformed identifier MUST be rejected as a
validation error, distinct from "not found" (FR-004); retrieval MUST have no side effects (FR-005,
constitution Principle VII's fail-fast spirit applied to reads: no silent fallbacks).

**Scale/Scope**: Same field-count scale as `001-field-geo-search`/`002-field-filter-pagination`
(up to 10,000 fields) — irrelevant to lookup cost since this is an indexed primary-key read.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Domain-Centric Design | PASS | `FieldNotFoundError` lives in `domain/field/exceptions.py`; no ORM/HTTP types in domain code. |
| II. Clean Architecture / Layered Boundaries | PASS | `application/field/get_field_by_id.py` depends only on the abstract `FieldRepository`; `presentation/` calls only the use case. |
| III. Strict Type Hinting | PASS | `find_by_id(field_id: UUID) -> Field | None` fully typed; mypy-checked. |
| IV. Immutability by Default | PASS | No new mutable state introduced; `Field` remains immutable-by-convention (create-only). |
| V. No Framework Contamination in Domain | PASS | UUID path-parameter parsing/coercion stays in `presentation/`; domain only ever sees a well-formed `UUID` or nothing. |
| VI. Repository Abstraction | PASS | `find_by_id` added to the existing abstract `FieldRepository` interface before being implemented in infrastructure. |
| VII. Fail Fast with Explicit Errors | PASS | `FieldNotFoundError` is raised explicitly by the use case rather than the endpoint silently returning `null`/empty. |
| VIII. Test-First & Fixture Discipline | PASS | Unit test for the use case's not-found branch runs with a fake repository, no DB; integration test for `find_by_id` uses the same testcontainers-backed isolated PostGIS instance as the rest of the field feature. |

**Result**: No unjustified violations. No new infrastructure services introduced.

## Project Structure

### Documentation (this feature)

```text
specs/003-field-detail-lookup/
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
│       ├── entities.py         # UNCHANGED (Field aggregate, from 001)
│       ├── exceptions.py       # EXTENDED: add FieldNotFoundError
│       └── repository.py       # EXTENDED: add find_by_id(field_id: UUID) -> Field | None
│
├── application/
│   └── field/
│       └── get_field_by_id.py  # NEW: GetFieldByIdUseCase (query handler)
│
├── infrastructure/
│   └── field/
│       └── postgis_repository.py # EXTENDED: implement find_by_id (primary-key lookup)
│
└── presentation/
    └── api/
        ├── field_router.py      # EXTENDED: add GET /fields/{field_id}
        └── schemas.py           # UNCHANGED: reuses the existing FieldResponse DTO from 001

tests/
├── unit/
│   └── application/field/       # NEW: GetFieldByIdUseCase not-found behavior, fake repository
├── integration/
│   └── infrastructure/field/    # EXTENDED: find_by_id hit/miss tests
└── contract/
    └── api/field/                # EXTENDED: GET /fields/{field_id} contract tests
```

**Structure Decision**: Extends the existing `001-field-geo-search` layout in place — no new
layer, module, or service. This is the smallest possible increment: one repository method, one use
case, one endpoint, reusing the `Field` entity and `FieldResponse` DTO already defined.

## Complexity Tracking

> No constitution violations require justification for this feature; no new infrastructure,
> dependencies, or architectural deviations are introduced.
