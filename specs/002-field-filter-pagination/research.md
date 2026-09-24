# Phase 0 Research: Field List Filtering & Pagination

## 1. Area-range filtering: persisted column vs. on-the-fly computation

**Decision**: Add a persisted `area_ha` numeric column to the existing `field` table, computed
once at field creation by reusing the same geodesic area calculation the domain layer already
performs for the 0.1 ha minimum-area rule (`001-field-geo-search` research.md Decision 2). Index
it with a btree index for efficient range queries.

**Rationale**: The area is already computed in the domain layer during field creation (FR-004 of
`001-field-geo-search`) — persisting it is just keeping that already-derived value instead of
recomputing it. A btree-indexed numeric range query (`WHERE area_ha BETWEEN :min AND :max`) is the
simplest and fastest way to satisfy SC-001 (<1s at ≤10,000 fields) and composes trivially with the
crop/owner filters in the same `WHERE` clause.

**Alternatives considered**:
- Compute `ST_Area(boundary::geography)` per row at query time — rejected: recomputes a value
  already known at creation time, on every filtered request, with no index support for the range
  comparison; unnecessary given the value never changes after creation (fields are create-only per
  `001-field-geo-search`).
- Store area in a separate lookup table — rejected: pure overhead: `area_ha` is a single scalar
  1:1 with `Field`, no different cardinality or lifecycle that would justify a separate table.

## 2. Pagination style

**Decision**: Offset-based pagination (`page`, `page_size` query parameters), matching the spec's
assumption of a standard page-number scheme with a default size of 20 and a maximum of 100.

**Rationale**: At the stated scale (≤10,000 fields, spec Scale/Scope), offset pagination's
well-known performance ceiling is not a concern, and it is simpler for API consumers to reason
about (jump to page N) than cursor-based pagination, matching the spec's Assumptions section.

**Alternatives considered**:
- Cursor/keyset pagination — rejected: adds complexity (opaque cursors, stable sort key
  requirements) not justified at this scale; spec's Assumptions already commit to page-number
  semantics.

## 3. Crop match semantics

**Decision**: Case-insensitive exact match on `crop` (SQL `LOWER(crop) = LOWER(:crop)`, or a
citext/lower-indexed comparison).

**Rationale**: Directly implements spec Assumptions ("crop filter matches on the field's exact
crop value, case-insensitive").

**Alternatives considered**: None — this was already resolved as an assumption in spec.md, not an
open technical question.

## 4. Owner match semantics

**Decision**: Case-insensitive substring match on `owner` (SQL `owner ILIKE '%' || :owner || '%'`).

**Rationale**: Directly implements spec Assumptions ("owner filter matches on a case-insensitive
partial (substring) match"). At ≤10,000 rows a sequential `ILIKE` scan easily meets SC-001; no
trigram/full-text index is needed at this scale.

**Alternatives considered**:
- `pg_trgm` trigram index for the `ILIKE` search — rejected for now: adds a PostgreSQL extension
  and index-maintenance cost not justified at 10,000 rows; revisit only if profiling shows owner
  search is a bottleneck at a larger scale than the spec targets.

## 5. Validation ordering (fail fast)

**Decision**: `FieldFilter` and `PageRequest` are validated at construction, in the domain layer,
before any repository/database call — `InvalidAreaRangeError` (min > max) and
`InvalidPageRequestError` (non-positive page/page_size, or page_size over the maximum) are raised
synchronously, consistent with how `001-field-geo-search`'s `Polygon`/`Coordinate` value objects
validate themselves.

**Rationale**: Constitution Principle VII (fail fast) and consistency with the existing feature's
established pattern — invalid requests never reach the database.

**Alternatives considered**:
- Let the database reject an inverted range via a `CHECK` constraint — rejected: applies to
  persisted rows, not incoming filter *requests*; doesn't help validate a query parameter before
  it's used, and pushes a domain rule into infrastructure.

**Output**: All Technical Context items are resolved; no `NEEDS CLARIFICATION` markers remain.
