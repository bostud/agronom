# Phase 0 Research: Agricultural Field Management & Point-Based Search

## 1. Polygon closed/non-self-intersecting validation

**Decision**: Validate that a submitted polygon is closed and non-self-intersecting inside the
`domain/field/value_objects.py` `Polygon` value object constructor, using Shapely
(`shapely.geometry.LinearRing` / `Polygon.is_simple`) purely as a computational-geometry library.

**Rationale**: Constitution Principle VII (fail fast) requires rejecting invalid input before any
persistence attempt, and Principle I/V require the domain layer to be free of database logic.
Validating in the domain layer means FR-002/FR-003 are enforced synchronously with no DB round
trip. Shapely has no database, HTTP, or web-framework dependency, so using it inside `domain/`
does not constitute "framework contamination" under Principle V (that principle targets ORM
classes, HTTP exceptions, and framework decorators specifically).

**Alternatives considered**:
- Hand-rolled ring-closure and segment-intersection checks — rejected: reimplements
  well-tested computational geometry, higher risk of subtle bugs (e.g. missed edge-touching
  cases) than a mature library.
- Deferring validation to PostGIS `ST_IsValid`/`ST_IsSimple` at insert time — rejected: violates
  fail-fast-in-domain, requires a DB round trip just to reject bad input, and pushes a domain rule
  (FR-002/FR-003) into infrastructure.

## 2. Minimum area (0.1 ha) calculation

**Decision**: Compute the polygon's enclosed area geodesically (accounting for the Earth's
curvature) using `pyproj.Geod.geometry_area_perimeter` inside the same domain-layer `Polygon`
value object, convert to hectares, and compare against the 0.1 ha threshold before the entity is
ever constructed.

**Rationale**: Field boundaries are supplied as latitude/longitude coordinates; a naive planar
(Euclidean) area calculation on raw degree values is inaccurate and the error scales with
latitude, which is unacceptable for a hard threshold used to accept/reject real submissions (spec
FR-004, edge case on marginal area). Geodesic calculation keeps this rule enforceable in the
domain layer, consistent with Decision 1.

**Alternatives considered**:
- Planar shoelace formula on raw lat/lon degrees — rejected: inaccurate, especially away from the
  equator.
- PostGIS `ST_Area` on a `geography` column at insert time — rejected for the same fail-fast/
  domain-purity reasons as Decision 1's rejected alternative. (PostGIS is still used later for
  indexed spatial *queries*, just not as the domain's validation authority.)

## 3. Persistence & spatial indexing

**Decision**: PostgreSQL 16+ with the PostGIS extension; store the field boundary in a `geometry`
(or `geography`) column; add a GIST index on that column; query with `ST_Contains`/`ST_Within`,
optionally pre-filtered by the `&&` bounding-box operator.

**Rationale**: This is a purpose-built spatial index that comfortably satisfies SC-003 (<1s at
≤10,000 fields) — typical point-in-polygon lookups against a GIST-indexed column at this scale run
in low single-digit milliseconds. GeoAlchemy2 maps the column at the infrastructure layer only;
`infrastructure/field/mappers.py` translates ORM records to/from the pure-Python domain `Field`
entity so no PostGIS/SQLAlchemy type ever crosses into `domain/` or `application/` (Principles V,
VI).

**Alternatives considered**:
- Application-level in-memory spatial index — rejected: doesn't persist, doesn't scale past a
  single process, reinvents what PostGIS already does well.
- Plain PostgreSQL with bounding-box columns and manual point-in-polygon math in Python —
  rejected: no index support for exact containment, worse accuracy, more code to maintain.

## 4. Caching layer (Redis / geohash)

**Decision**: Not included in this feature's implementation. See `plan.md` Complexity Tracking.

**Rationale**: No requirement in spec.md calls for sub-second-scale caching; SC-003's <1s target
at ≤10,000 fields is met by Decision 3 alone with wide margin. A cache-aside layer adds a second
stateful service, invalidation logic on every field create, and operational surface area with no
measured need.

**Alternatives considered**:
- Redis geohash cache-aside (as proposed) — retained as a documented future optimization, not
  adopted now; revisit only if production profiling shows the database is the bottleneck at a
  scale beyond SC-003.

## 5. Test isolation strategy

**Decision**: Domain unit tests (`tests/unit/domain/field/`) run with zero external dependencies.
Integration tests (`tests/integration/infrastructure/field/`) use testcontainers-python to start a
fresh, isolated PostGIS container per test run/session.

**Rationale**: Constitution Principle VIII requires integration tests to use isolated containers
or transactional rollbacks rather than a shared database, preventing state leakage between test
runs.

**Alternatives considered**:
- Shared local/dev PostgreSQL instance for integration tests — rejected: violates Principle VIII,
  risks flaky/order-dependent tests.

## 6. Containerization

**Decision**: Docker Compose defines `web` (FastAPI app) and `db` (`postgis/postgis:16-3.4`)
services for local development and CI parity. No `cache` service, consistent with Decision 4.

**Rationale**: Matches the stakeholder's infrastructure-parity goal without provisioning a service
(Redis) this feature doesn't use yet.

**Alternatives considered**:
- Include a `cache` (Redis) service now for future-proofing — rejected: YAGNI; add it in the same
  change that actually introduces caching, per Decision 4.

## 7. API shape

**Decision**: Two REST endpoints exposed via a FastAPI router: `POST /fields` (create) and
`GET /fields/search?lat=&lon=` (point search). Documented in `contracts/field-api.md`.

**Rationale**: Matches the two user stories in spec.md directly; REST is the project's established
presentation pattern (constitution Technology & Architecture Constraints section).

**Alternatives considered**: None — no alternative interface style was in scope or requested.

**Output**: All Technical Context items are resolved; no `NEEDS CLARIFICATION` markers remain.
