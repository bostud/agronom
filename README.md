# agronom
Менеджер твоєї аграрки

Agronom stores agricultural fields as named polygons with an owner and a crop. It finds the fields that contain a map point in milliseconds, using a PostGIS spatial index.

- [Usage](#usage)
  - [Requirements](#requirements)
  - [Quick start](#quick-start)
  - [Make commands](#make-commands)
  - [Configuration](#configuration)
  - [API](#api)
  - [Tests](#tests)
  - [Running the app outside Docker](#running-the-app-outside-docker)
- [Design](#design)
  - [Architecture](#architecture)
  - [Domain model](#domain-model)
  - [Validation rules](#validation-rules)
  - [Find fields by point](#find-fields-by-point)
  - [Project layout](#project-layout)
  - [Further reading](#further-reading)

---

## Usage

### Requirements

- Docker with Docker Compose v2
- GNU Make
- Python 3.12. Only needed to run tests or to run the app outside Docker.

### Quick start

```bash
make up            # build and start the app and PostGIS
make migrate       # create the field table and indexes
make seed_fields   # optional: add 100 sample fields near Kyiv
```

The API runs at http://localhost:8000. Interactive docs are at http://localhost:8000/api/docs.

`make seed_fields` prints a ready-made `curl` command that finds one of the seeded fields by a point inside it.

### Make commands

Run `make` or `make help` to list them.

| Command | What it does |
|---|---|
| `make up` | Builds the image and starts the app and the database, then waits until they are up |
| `make down` | Stops the containers. Database data stays in the `agronom-db-data` volume |
| `make logs` | Follows the app logs |
| `make migrate` | Rebuilds the image and runs `alembic upgrade head` inside a container |
| `make seed_fields` | Runs the migrations, then generates sample fields. Options: `COUNT=500` sets the number of fields (default 100). `SEED=42` makes the output reproducible |
| `make install` | Creates `.venv` and installs the project with dev dependencies |
| `make test` | Runs the migrations, then the whole test suite |
| `make test-unit` | Runs unit tests only. Needs no Docker and no database |

About the sample data:
- Seeded fields sit on a grid of non-overlapping cells starting at 50.0°N, 30.0°E, one field per cell, each 11–54 ha.
- Every seed run fills the same grid again, so a second run adds fields on top of the first ones.
- To start from an empty database, run `docker compose down -v`, then `make up migrate`.

### Configuration

| Variable | Default | Used by |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://agronom:agronom@localhost:5432/agronom` | App, Alembic, seed script |

`docker-compose.yml` sets `DATABASE_URL` for the `web` container so it points at the `db` service.

Domain constants are in [src/settings.py](src/settings.py):

| Constant | Value | Meaning |
|---|---|---|
| `MIN_POLYGON_AREA_HA` | `0.1` | Smallest allowed field area |
| `DEFAULT_LIMIT` | `20` | Default page size of `GET /api/fields` |
| `MAX_LIMIT` | `100` | Largest allowed page size |
| `GEOD_ELLIPSOID` | `WGS84` | Ellipsoid for geodesic areas and distances |

### API

All endpoints are under `/api/fields`. Geometry uses GeoJSON with `[longitude, latitude]` order in WGS 84 (EPSG:4326).

| Method | Path | Purpose | Errors |
|---|---|---|---|
| `POST` | `/api/fields` | Create a field | 422 for an invalid polygon or missing attribute |
| `GET` | `/api/fields` | List fields with filters, one page at a time | 422 for invalid paging or area range |
| `GET` | `/api/fields/find-by-point?lat=&lon=` | Find the fields that contain a point | 422 for out-of-range coordinates |
| `GET` | `/api/fields/{id}` | Get one field with its geometry | 404 if it doesn't exist |

**Create a field**

```bash
curl -s -X POST http://localhost:8000/api/fields \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Північна ділянка",
    "owner": "ФГ «Колос»",
    "crop": "Пшениця",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [30.5234, 50.4501],
        [30.5250, 50.4501],
        [30.5250, 50.4515],
        [30.5234, 50.4515],
        [30.5234, 50.4501]
      ]]
    }
  }'
```

This returns `201` with the stored field, including a generated `id`, the computed `area_ha` and `created_at`.

**Find fields by point**

```bash
curl -s "http://localhost:8000/api/fields/find-by-point?lat=50.4508&lon=30.5242"
```

```json
{
  "query_point": { "lon": 30.5242, "lat": 50.4508 },
  "fields": [
    {
      "id": "…",
      "name": "Північна ділянка",
      "area_ha": 1.77,
      "crop": "Пшениця",
      "owner": "ФГ «Колос»",
      "distance_to_center_m": 0.0
    }
  ],
  "query_time_ms": 3.2
}
```

- Fields are sorted by `distance_to_center_m`, closest first.
- A point outside every field returns `"fields": []`, not an error.

**List fields**

```bash
curl -s "http://localhost:8000/api/fields?crop=пшениця&owner=колос&min_area=1&max_area=50&limit=20&offset=0"
```

| Parameter | Behaviour |
|---|---|
| `crop` | Exact match, ignoring case |
| `owner` | Substring match, ignoring case |
| `min_area`, `max_area` | Area in hectares, inclusive. `min_area` must not exceed `max_area` |
| `limit` | 1–100, default 20 |
| `offset` | 0 or more, default 0 |

The response is `{"total": <all matching fields>, "fields": [...]}`, sorted by name and then by id. List items leave out the geometry. Use `GET /api/fields/{id}` to get it.

### Tests

```bash
make install     # once
make test        # everything
make test-unit   # fast, no Docker
```

| Suite | Path | Needs |
|---|---|---|
| Unit | `tests/unit` | Nothing. Covers domain rules and use cases with fake repositories |
| Integration | `tests/integration` | Docker. `testcontainers` starts a separate PostGIS container |
| Contract | `tests/contract` | The running database from `make up`. Calls the HTTP endpoints through FastAPI |

Contract tests write into the same database the app uses, so test fields stay in it afterwards.

### Running the app outside Docker

```bash
docker compose up -d db
make install
.venv/bin/alembic upgrade head
.venv/bin/uvicorn src.presentation.api.main:app --reload
```

The default `DATABASE_URL` already points at the database on `localhost:5432`.

---

## Design

### Architecture

The code follows Clean Architecture in four layers. Dependencies point inward:

```mermaid
flowchart LR
  subgraph Presentation
    R["field_router.py"] --> S["schemas.py<br/>GeoJSON ⇄ domain"]
    R --> D["dependencies.py<br/>DI: Session → Repo → UseCase"]
  end
  subgraph Application
    UC["CreateField / ListFields /<br/>FindFieldsByPoint / GetFieldById"]
  end
  subgraph Domain
    E["Field entity"] --> VO["Coordinate · Polygon · FieldFilter"]
    P["PageRequest · Page"]
    REPO[["FieldRepository (ABC)"]]
  end
  subgraph Infrastructure
    PR["PostgisFieldRepository"] --> M["mappers.py"] --> FM["FieldModel (ORM)"]
  end
  R --> UC --> REPO
  PR -. implements .-> REPO
  D --> PR
  FM --> DB[("PostGIS: field table")]
```

| Layer | Path | Responsibility |
|---|---|---|
| Domain | `src/domain` | Entities, value objects, validation rules, and the abstract repository. It imports nothing from the other layers except `src/settings.py`, which uses only the standard library |
| Application | `src/application` | One class per use case. Each one works only with the `FieldRepository` interface |
| Infrastructure | `src/infrastructure` | SQLAlchemy/GeoAlchemy model, domain ⇄ ORM mappers, PostGIS repository |
| Presentation | `src/presentation/api` | FastAPI router, request/response schemas, dependency injection |

For each request, `dependencies.py` opens a session and builds the repository and the use case. It commits when the request succeeds and rolls back when it fails.

The development specs for each feature are in [specs/](specs/):
- 001: create fields and search by point
- 002: filtering and pagination
- 003: get a field by id

### Domain model

```mermaid
classDiagram
  class Field {
    <<entity>>
    +UUID id
    +str name
    +str owner
    +str crop
    +Polygon geometry
    +datetime created_at
    +create()$ Field
    +area_ha() float
  }
  class Polygon {
    <<value object>>
    +tuple vertices
    +area_ha() float
    +centroid() Coordinate
  }
  class Coordinate {
    <<value object>>
    +float latitude
    +float longitude
    +distance_to_m(other) float
  }
  class FieldFilter {
    <<value object>>
    +str crop
    +str owner
    +float min_area_ha
    +float max_area_ha
  }
  class PageRequest {
    +int limit
    +int offset
  }
  class Page~T~ {
    +tuple items
    +int total
    +int limit
    +int offset
  }
  class FieldMatch {
    +Field field
    +float distance_to_center_m
  }
  class FieldRepository {
    <<abstract>>
    +save(Field)
    +find_containing_point(Coordinate) list
    +find_page(FieldFilter, PageRequest) Page
    +find_by_id(UUID) Field
  }
  class PostgisFieldRepository
  class FieldModel {
    <<ORM table field>>
    +UUID id
    +VARCHAR name
    +VARCHAR owner
    +VARCHAR crop
    +POLYGON_4326 geometry
    +FLOAT area_ha
    +TIMESTAMPTZ created_at
  }
  Field *-- Polygon
  Polygon *-- "4..*" Coordinate
  FieldMatch --> Field
  FieldRepository ..> Field
  PostgisFieldRepository ..|> FieldRepository
  PostgisFieldRepository ..> FieldModel : mappers
```

- Domain objects are immutable Pydantic models (`frozen=True`).
- `Polygon` computes area as a geodesic area on the WGS 84 ellipsoid (pyproj). It computes the centroid on the plane with Shapely.
- The `field` table has a GIST index on `geometry` (`ix_field_geometry_gist`) and a btree index on `area_ha` (`ix_field_area_ha`).
- `area_ha` is stored in the table so area filters can use its index. The domain entity computes it from the geometry instead.
- Migrations are in [migrations/versions](migrations/versions).

### Validation rules

Every value object checks itself when it is created. The router turns each domain error into an HTTP response.

| Object | Rule | Error | HTTP |
|---|---|---|---|
| `Coordinate` | Latitude in [-90, 90], longitude in [-180, 180] | `InvalidCoordinateError` | 422 |
| `Polygon` | At least 3 distinct vertices, and the first vertex equals the last | `PolygonNotClosedError` | 422 |
| `Polygon` | Edges don't cross each other (`shapely.is_simple`) | `SelfIntersectingPolygonError` | 422 |
| `Polygon` | Geodesic area ≥ 0.1 ha | `PolygonTooSmallError` | 422 |
| `Field.create` | `name`, `owner`, `crop`, `geometry` are present and not blank | `MissingFieldAttributeError` | 422 |
| `FieldFilter` | `min_area_ha ≤ max_area_ha` | `InvalidAreaRangeError` | 422 |
| `PageRequest` | `1 ≤ limit ≤ 100`, `offset ≥ 0` | `InvalidPageRequestError` | 422 |
| `GetFieldByIdUseCase` | A field with the id exists | `FieldNotFoundError` | 404 |

### Find fields by point

This is the main feature. The client sends coordinates and gets back every field that contains the point, closest centre first. The spec's success criterion SC-003 requires an answer in under one second. The response includes `query_time_ms` so you can check this.

```mermaid
sequenceDiagram
  actor C as Client
  participant API as field_router
  participant DI as dependencies
  participant UC as FindFieldsByPointUseCase
  participant Repo as PostgisFieldRepository
  participant PG as PostGIS
  participant Map as mappers

  C->>API: GET /api/fields/find-by-point?lat=50.45&lon=30.52
  API->>DI: build Session → Repo → UseCase
  API->>API: Coordinate(lat, lon), range check (else 422)
  API->>UC: execute(point), timer starts
  UC->>Repo: find_containing_point(point)
  Repo->>PG: SELECT … WHERE geometry && :pt AND ST_Contains(geometry, :pt)
  Note over PG: 1) GIST index scan on bounding boxes<br/>2) exact point-in-polygon test
  PG-->>Repo: FieldModel rows
  loop each row
    Repo->>Map: model_to_field: WKB → Shapely → Polygon → Field
  end
  Repo-->>UC: list of Field
  loop each field
    UC->>UC: centroid → geodesic distance to point
  end
  UC->>UC: sort by distance_to_center_m
  UC-->>API: list of FieldMatch, timer stops
  API-->>C: 200 query_point, fields, query_time_ms
  DI->>DI: session.commit(), close()
```

**Why it is fast**

1. **The query filters in two steps** ([postgis_repository.py](src/infrastructure/field/postgis_repository.py)).
   - `geometry && point` compares bounding boxes, which the GIST index answers without reading any polygons. This narrows the table to a few candidates in roughly O(log n).
   - `ST_Contains` then runs the exact point-in-polygon test on those candidates only.
   - `ST_Contains` already runs the bounding-box check internally, so the explicit `&&` is redundant. It is harmless and makes the use of the index obvious.
2. **The model sets `spatial_index=False`.** The GIST index is created in migration `0001` instead, so GeoAlchemy doesn't create a second copy of it.
3. **Ranking happens in Python.** A point usually lies in one or two fields, so computing their distances and sorting them costs almost nothing.

**Behaviour to know about**

- **Boundary points don't match.** A point exactly on a field's edge is not returned, because `ST_Contains` excludes the boundary. `ST_Covers` includes it.
- **Rows are validated again when read.** `model_to_field` rebuilds each `Polygon`, which runs the self-intersection check and the area calculation again. The response also recomputes `area_ha`, even though the table stores it. This is cheap for a few matches but adds up on `GET /api/fields?limit=100`.
- **"Distance to centre" is an approximation.** The centroid is computed on raw longitude/latitude degrees as if they were a flat plane. The distance to it is geodesic. This is accurate enough for field-sized polygons.
- **Route order matters.** `/find-by-point` is declared before `/{field_id}`. If they were swapped, `find-by-point` would be parsed as a UUID and the request would fail with 422.
- **`query_time_ms` doesn't cover the whole request.** It measures the use case only: the database query, mapping and sorting. Dependency setup and response serialization are not included.

### Project layout

```
src/
  settings.py                 environment and domain constants
  domain/
    common/pagination.py      PageRequest, Page
    field/                    Field entity, value objects, exceptions, FieldRepository
  application/field/          one module per use case
  infrastructure/field/       ORM model, mappers, PostgisFieldRepository
  presentation/api/           FastAPI app, router, schemas, dependencies
  scripts/seed_fields.py      sample data generator (make seed_fields)
migrations/                   Alembic environment and revisions
tests/{unit,integration,contract}/
specs/                        feature specs, plans and API contracts
```

### Further reading

- [PostGIS introduction workshop](https://postgis.net/workshops/postgis-intro/). See the chapters on [spatial indexing](https://postgis.net/workshops/postgis-intro/indexing.html) and [DE-9IM](https://postgis.net/workshops/postgis-intro/de9im.html).
- PostGIS reference: [`ST_Contains`](https://postgis.net/docs/ST_Contains.html), [`ST_Covers`](https://postgis.net/docs/ST_Covers.html), [`&&`](https://postgis.net/docs/geometry_overlaps.html).
- [PostgreSQL GiST indexes](https://www.postgresql.org/docs/current/gist.html)
- [GeoJSON, RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946) and [EPSG:4326](https://epsg.io/4326)
- [Shapely manual](https://shapely.readthedocs.io/en/stable/manual.html), [pyproj Geod](https://pyproj4.github.io/pyproj/stable/api/geod.html), [GeoAlchemy2](https://geoalchemy-2.readthedocs.io/)
- [FastAPI dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) and [dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
- [Architecture Patterns with Python](https://www.cosmicpython.com/book/preface.html): Repository, use cases and DDD in Python
- [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
