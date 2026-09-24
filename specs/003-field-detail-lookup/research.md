# Phase 0 Research: Retrieve a Specific Field

## 1. Malformed-identifier detection (FR-004)

**Decision**: Rely on FastAPI's automatic path-parameter type coercion — declaring the
`field_id` path parameter as `UUID` — to reject syntactically invalid identifiers with a `422`
before the request ever reaches the application/domain layers. No new domain exception is
introduced for this case.

**Rationale**: A malformed identifier (e.g. "not-a-uuid") is a request-*format* problem, not a
business rule — it's indistinguishable from any other malformed-input case FastAPI/Pydantic
already handles at the boundary. Introducing a domain exception for "this string isn't a UUID"
would duplicate what the type system already guarantees once the value reaches `domain/`/
`application/`: by the time `GetFieldByIdUseCase` runs, `field_id` is always a well-formed `UUID`.

**Alternatives considered**:
- A domain-level `InvalidFieldIdentifierError`, parsed and raised manually in the use case —
  rejected: pure duplication of type coercion already provided by the framework at the
  presentation boundary, adding a code path that can never actually be exercised if the router is
  implemented correctly.

## 2. Not-found handling (FR-003)

**Decision**: `FieldRepository.find_by_id` returns `Field | None` (`None` when no matching row
exists). `GetFieldByIdUseCase` raises a new domain exception, `FieldNotFoundError`, when it
receives `None`. `presentation/api/field_router.py` maps `FieldNotFoundError` to `404 Not Found`.

**Rationale**: Consistent with constitution Principle VII (fail fast, explicit domain exceptions)
and with how `001-field-geo-search` already handles its other domain error cases — the use case
layer, not the router, decides that "no such field" is an error condition; the router only knows
how to translate it to HTTP.

**Alternatives considered**:
- Repository raises `FieldNotFoundError` itself — rejected: keeps the repository's contract
  simpler (a lookup either finds something or doesn't; deciding *whether that's an error* is an
  application-layer concern, not a persistence concern) and mirrors the `Optional`-return pattern
  most repository/DAO interfaces use for single-item lookups.

## 3. Reuse of existing response shape

**Decision**: Reuse the `FieldResponse` Pydantic DTO already defined in
`src/presentation/api/schemas.py` (from `001-field-geo-search`) for the `200` response — no new
DTO needed.

**Rationale**: FR-002 asks for exactly the same detail set (name, owner, crop, geometry, area)
already returned by `POST /fields`'s `201` response and present in `002-field-filter-pagination`'s
list items. A separate DTO would just be a duplicate definition to keep in sync.

**Alternatives considered**: A dedicated `FieldDetailResponse` — rejected: no field-level
difference from the existing `FieldResponse` justifies a second type.

**Output**: All Technical Context items are resolved; no `NEEDS CLARIFICATION` markers remain.
