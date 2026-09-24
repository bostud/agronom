# Implementation Plan: Field List Filtering & Pagination

**Branch**: `002-field-filter-pagination` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-field-filter-pagination/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Add a paginated field-listing capability, with optional filters by crop (exact, case-insensitive),
owner (partial, case-insensitive), and area range (inclusive min/max, hectares), to the existing
`Field` aggregate introduced in `001-field-geo-search`. Technical approach: extend the existing
`FieldRepository` interface with a `find_page` method; add reusable, feature-agnostic `PageRequest`
and `Page[T]` value objects under `domain/common/`; add a `FieldFilter` value object under
`domain/field/`; implement filtering/pagination in `PostgisFieldRepository` with a new indexed,
persisted `area_ha` column (computed once at field creation, reusing the geodesic area calculation
already performed for the 0.1 ha minimum-area rule); expose a `GET /fields` endpoint. No new
external dependencies or services are introduced — this is a read path over data that already
exists.

## Technical Context

**Language/Version**: Python 3.12 (unchanged from `001-field-geo-search`)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x + GeoAlchemy2 — all already present
from `001-field-geo-search`; no new libraries required.

**Storage**: The existing PostgreSQL 16+/PostGIS `field` table from `001-field-geo-search`, extended
with one new persisted column (`area_ha`) and its index (see research.md Decision 1).

**Testing**: pytest + pytest-asyncio + testcontainers-python (unchanged).

**Target Platform**: Linux server, containerized (unchanged).

**Project Type**: web-service (extension of the existing backend).

**Performance Goals**: Any page of the (optionally filtered) list returns in under 1 second for up
to 10,000 fields (spec SC-001).

**Constraints**: Filters combine with logical AND (FR-009); invalid page number/size or an
inverted area range are rejected with explicit validation errors, never silently corrected
(FR-003, FR-010, FR-013, constitution Principle VII); domain layer remains free of ORM/HTTP
dependencies (constitution Principles I, V).

**Scale/Scope**: Up to 10,000 fields (spec SC-001), same scale as `001-field-geo-search`. Default
page size 20, maximum page size 100 (spec Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Domain-Centric Design | PASS | `FieldFilter`, `PageRequest`, `Page[T]` live in `domain/`; no ORM/HTTP/pagination-framework types leak into domain code. |
| II. Clean Architecture / Layered Boundaries | PASS | `application/field/list_fields.py` depends only on the abstract `FieldRepository`; `PostgisFieldRepository` (infrastructure) implements the new `find_page` method; `presentation/` calls only the use case. |
| III. Strict Type Hinting | PASS | `Page[T]` is a typed generic; all new code fully type-hinted, mypy-checked. |
| IV. Immutability by Default | PASS | `FieldFilter` and `PageRequest` are frozen value objects; `Page[T]` is a frozen result container. |
| V. No Framework Contamination in Domain | PASS | SQLAlchemy `LIMIT`/`OFFSET`/`ILIKE`/range-query logic is confined to `PostgisFieldRepository`; domain only expresses filter/paging *intent*, not SQL. |
| VI. Repository Abstraction | PASS | `find_page` is added to the existing abstract `FieldRepository` interface in `domain/field/repository.py` before being implemented in infrastructure. |
| VII. Fail Fast with Explicit Errors | PASS | New domain exceptions `InvalidAreaRangeError` and `InvalidPageRequestError` reject bad input at construction, before any query runs (FR-010, FR-013). |
| VIII. Test-First & Fixture Discipline | PASS | Domain tests for `FieldFilter`/`PageRequest` validation run with no DB; repository filtering/pagination is covered by testcontainers-backed integration tests, consistent with `001-field-geo-search`. |

**Result**: No unjustified violations. No new infrastructure services introduced.

## Project Structure

### Documentation (this feature)

```text
specs/002-field-filter-pagination/
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
│   ├── common/
│   │   └── pagination.py       # NEW: PageRequest, Page[T] (generic, feature-agnostic)
│   └── field/
│       ├── entities.py         # UNCHANGED (Field aggregate, from 001)
│       ├── value_objects.py    # EXTENDED: add FieldFilter
│       ├── exceptions.py       # EXTENDED: add InvalidAreaRangeError, InvalidPageRequestError
│       └── repository.py       # EXTENDED: add find_page(filter, page_request) -> Page[Field]
│
├── application/
│   └── field/
│       └── list_fields.py      # NEW: ListFieldsUseCase (query handler)
│
├── infrastructure/
│   └── field/
│       ├── models.py            # EXTENDED: add area_ha column + index
│       ├── mappers.py           # EXTENDED: populate/read area_ha
│       └── postgis_repository.py # EXTENDED: implement find_page
│
└── presentation/
    └── api/
        ├── field_router.py      # EXTENDED: add GET /fields
        └── schemas.py           # EXTENDED: add filter/pagination request+response DTOs

migrations/
└── versions/
    └── <new revision>           # NEW: add area_ha column + btree index to field table

tests/
├── unit/
│   └── domain/field/            # EXTENDED: FieldFilter, PageRequest validation tests
├── integration/
│   └── infrastructure/field/    # EXTENDED: find_page filtering/pagination tests
└── contract/
    └── api/field/                # EXTENDED: GET /fields contract tests
```

**Structure Decision**: Extends the existing `001-field-geo-search` layout in place — same four
DDD layers, same `field/` submodule per layer — plus one new `domain/common/` module for the
pagination primitives, since `Page[T]`/`PageRequest` are generic and not inherently field-specific.
No new top-level project or service is introduced.

## Complexity Tracking

> No constitution violations require justification for this feature. One architectural decision
> worth surfacing (not a violation): a new `area_ha` column is added to the existing `field` table
> so area-range filtering can use a plain indexed numeric comparison instead of computing
> `ST_Area` per row on every filtered query. See research.md Decision 1 for the full rationale.
