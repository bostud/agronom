# Phase 1 Data Model: Agricultural Field Management & Point-Based Search

## Value Objects (domain, immutable)

### Coordinate

Represents a single point on the Earth's surface.

| Field | Type | Rule |
|---|---|---|
| `latitude` | float | Required. Must be in the range -90.0 to 90.0 (spec Edge Cases: "out-of-range latitude or longitude" MUST be rejected). |
| `longitude` | float | Required. Must be in the range -180.0 to 180.0 (spec Edge Cases). |

Immutable (frozen); invalid values raise `InvalidCoordinateError` at construction (FR-009).

### Polygon

Represents a field's boundary as an ordered ring of coordinates.

| Field | Type | Rule |
|---|---|---|
| `vertices` | tuple[Coordinate, ...] | Required, minimum 3 distinct points before closure (spec Edge Cases: "fewer than 3 distinct vertices ... MUST be rejected as an invalid geometry"). |

Derived/validated at construction (all fail-fast per constitution Principle VII):

- **Closed**: "the boundary geometry to be a closed polygon (its first and last points
  coincide)" (FR-002) — the ring's first and last coordinate MUST be equal; if not, raise
  `PolygonNotClosedError`.
- **Non-self-intersecting**: "System MUST reject boundary geometries whose edges self-intersect"
  (FR-003) — if any two non-adjacent edges intersect, raise `SelfIntersectingPolygonError`.
- **Minimum area**: "System MUST compute the enclosed area of the boundary geometry and MUST
  reject submissions where that area is smaller than 0.1 hectares" (FR-004), computed
  geodesically (see research.md Decision 2) — if area < 0.1 ha, raise `PolygonTooSmallError`,
  and per the spec's edge case the error MUST state the computed area.

Immutable (frozen) once constructed — a `Polygon` that exists is, by construction, always closed,
simple, and ≥0.1 ha; there is no code path that produces an "invalid" `Polygon` instance.

## Entities

### Field (Aggregate Root)

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | System-generated on creation. |
| `name` | str | Required, non-empty ("System MUST reject a field creation request that is missing name, owner, crop, or geometry, identifying which attribute(s) are missing" — FR-005). |
| `owner` | str | Required, non-empty (FR-005). Descriptive attribute only — no separate owner registry (spec Assumptions). |
| `crop` | str | Required, non-empty (FR-005). Free-text/single-selection value describing what is currently planted (spec Assumptions). |
| `boundary` | Polygon | Required (FR-005); see `Polygon` value object above for all shape/area rules. |
| `created_at` | datetime | System-generated on creation. |

**Invariants**:
- A `Field` cannot exist with a missing `name`, `owner`, `crop`, or `boundary` (FR-005) — the
  aggregate's constructor/factory raises `MissingFieldAttributeError` naming the missing
  attribute(s) if violated.
- A `Field`'s `boundary` is always a valid `Polygon` per the value object's own invariants (closed,
  simple, ≥0.1 ha) — the aggregate does not re-validate geometry rules itself; it delegates to the
  `Polygon` value object, which cannot be constructed in an invalid state.
- Overlapping boundaries between different `Field` instances are explicitly allowed (spec
  Assumptions) — no cross-field uniqueness/exclusivity constraint exists.

**Relationships**: None to other entities in this feature. `owner` and `crop` are plain descriptive
attributes, not references to other aggregates (spec Assumptions).

## Domain Exceptions

| Exception | Raised When | Used By |
|---|---|---|
| `InvalidCoordinateError` | Latitude/longitude outside valid range, or a search point is malformed | `Coordinate`, search use case (FR-009) |
| `PolygonNotClosedError` | First and last vertex of a submitted boundary do not coincide | `Polygon` (FR-002) |
| `SelfIntersectingPolygonError` | Two non-adjacent boundary edges intersect | `Polygon` (FR-003) |
| `PolygonTooSmallError` | Computed geodesic area < 0.1 hectares; message states the computed area | `Polygon` (FR-004, edge case) |
| `MissingFieldAttributeError` | `name`, `owner`, `crop`, or `boundary` absent on creation; message names missing attribute(s) | `Field` factory (FR-005) |

All inherit from a common `FieldDomainError` base so application/presentation code can catch them
uniformly, while still allowing specific handling (e.g. mapping each to a distinct HTTP 4xx
response in `presentation/api/field_router.py`).

## Repository Interface (domain, abstract)

```text
FieldRepository (domain/field/repository.py)
  - save(field: Field) -> None
  - find_containing_point(point: Coordinate) -> list[Field]
```

`find_containing_point` backs User Story 2 (FR-007, FR-008): returns an empty list — never an
error — when no field's boundary contains the point. The concrete `PostgisFieldRepository`
(infrastructure) implements this using an indexed `ST_Contains`/`ST_Within` query.

## State Transitions

None. `Field` is create-only for this feature (no update/delete use case is in scope per
spec.md's two user stories).
