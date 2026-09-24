# Phase 1 Data Model: Field List Filtering & Pagination

## Changes to Existing Entities

### Field (from `001-field-geo-search`, extended)

| Field | Type | Change |
|---|---|---|
| `area_ha` | float | **NEW**, persisted. Computed once at creation from `boundary`'s geodesic area (same calculation already used to enforce the 0.1 ha minimum in `001-field-geo-search` FR-004). Indexed (btree) to support range filtering. Not user-supplied — derived and immutable after creation, like the rest of `boundary`. |

No other `Field` attributes change. `Field` remains create-only; this feature adds no write path.

## New Value Objects (domain, immutable)

### FieldFilter (`domain/field/value_objects.py`)

| Field | Type | Rule |
|---|---|---|
| `crop` | str \| None | Optional. When present, matched case-insensitively, exact value (FR-006, spec Assumptions). |
| `owner` | str \| None | Optional. When present, matched case-insensitively as a substring (FR-007, spec Assumptions). |
| `min_area_ha` | float \| None | Optional. Inclusive lower bound in hectares (FR-008). |
| `max_area_ha` | float \| None | Optional. Inclusive upper bound in hectares (FR-008). |

**Invariant**: If both `min_area_ha` and `max_area_ha` are supplied, `min_area_ha` MUST NOT exceed
`max_area_ha` — "System MUST reject a request where the supplied minimum area is greater than the
supplied maximum area" (FR-010). Violation raises `InvalidAreaRangeError` at construction.

An "empty" `FieldFilter` (all fields `None`) is valid and represents "no filtering" (FR-012).
When more than one of `crop`/`owner`/`min_area_ha`/`max_area_ha` is set, all supplied conditions
apply together (logical AND) — "System MUST return only fields that satisfy every supplied
filter" (FR-009).

### PageRequest (`domain/common/pagination.py`)

| Field | Type | Rule |
|---|---|---|
| `page` | int | Required, MUST be ≥ 1 (FR-013); defaults to 1 when not supplied by the caller (FR-002). |
| `page_size` | int | Required, MUST be ≥ 1 and ≤ 100 (FR-003, FR-013); defaults to 20 when not supplied by the caller (FR-003, spec Assumptions). |

**Invariant**: `page < 1`, `page_size < 1`, or `page_size > 100` raises `InvalidPageRequestError`
at construction, stating the violated bound in the message (FR-003, FR-013).

### Page[T] (`domain/common/pagination.py`)

Generic, reusable paginated-result container — not specific to `Field`.

| Field | Type | Rule |
|---|---|---|
| `items` | tuple[T, ...] | The page's results; may be empty (FR-005, FR-011). |
| `page` | int | Echoes the requested page number. |
| `page_size` | int | Echoes the requested page size. |
| `total_items` | int | Total count of items matching the filter, across all pages (FR-004). |
| `total_pages` | int | `ceil(total_items / page_size)`, or `0` when `total_items` is `0` (FR-004). |

Immutable (frozen); constructed only by the repository/use-case layer from a query result, never
mutated afterward.

## Domain Exceptions (additions to `domain/field/exceptions.py`)

| Exception | Raised When | Used By |
|---|---|---|
| `InvalidAreaRangeError` | `FieldFilter.min_area_ha > FieldFilter.max_area_ha` | `FieldFilter` (FR-010) |
| `InvalidPageRequestError` | `page < 1`, `page_size < 1`, or `page_size > 100` | `PageRequest` (FR-003, FR-013) |

Both inherit from the existing `FieldDomainError` base (`001-field-geo-search`), so
`presentation/api/field_router.py` can continue mapping any `FieldDomainError` subtype to a `422`
response uniformly.

## Repository Interface (extension to `domain/field/repository.py`)

```text
FieldRepository (existing interface, extended)
  - save(field: Field) -> None                                              # from 001, unchanged
  - find_containing_point(point: Coordinate) -> list[Field]                 # from 001, unchanged
  - find_page(filter: FieldFilter, page_request: PageRequest) -> Page[Field]  # NEW
```

`find_page` backs all three user stories (US1: pagination with an empty `FieldFilter`; US2: crop/
owner filtering; US3: area-range filtering) — one method serves all of them since filters are
independently optional (FR-012) and combine via AND (FR-009). The concrete
`PostgisFieldRepository` (infrastructure) implements it as a single parameterized SQL query with
`WHERE`/`LIMIT`/`OFFSET`, plus a `COUNT(*)` (or window function) for `total_items`.

## State Transitions

None. This feature is read-only (spec Assumptions) — it introduces no new entity lifecycle.
