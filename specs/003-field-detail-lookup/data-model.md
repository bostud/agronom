# Phase 1 Data Model: Retrieve a Specific Field

## Entities

No changes to `Field` (from `001-field-geo-search`, as extended by `002-field-filter-pagination`
with `area_ha`). This feature is a pure read of the existing aggregate by its existing `id`.

## Domain Exceptions (addition to `domain/field/exceptions.py`)

| Exception | Raised When | Used By |
|---|---|---|
| `FieldNotFoundError` | `FieldRepository.find_by_id` returns `None` for the given identifier | `GetFieldByIdUseCase` (FR-003) |

Inherits from the existing `FieldDomainError` base (`001-field-geo-search`), so
`presentation/api/field_router.py`'s existing domain-exception-to-HTTP mapping pattern extends
naturally — this one maps to `404` rather than `422` (see contracts/field-detail-api.md).

## Repository Interface (extension to `domain/field/repository.py`)

```text
FieldRepository (existing interface, extended)
  - save(field: Field) -> None                                              # from 001, unchanged
  - find_containing_point(point: Coordinate) -> list[Field]                 # from 001, unchanged
  - find_page(filter: FieldFilter, page_request: PageRequest) -> Page[Field]  # from 002, unchanged
  - find_by_id(field_id: UUID) -> Field | None                              # NEW
```

`find_by_id` performs an indexed primary-key lookup and returns `None` when no row matches — it
does not raise. Deciding that "no result" is an error condition (FR-003) is the use case's
responsibility, not the repository's (research.md Decision 2).

## State Transitions

None. This feature is read-only (spec Assumptions) — it introduces no new entity lifecycle and
performs no writes (FR-005).
