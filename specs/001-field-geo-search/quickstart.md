# Quickstart: Agricultural Field Management & Point-Based Search

Validates both user stories end-to-end. See [data-model.md](./data-model.md) for entity/validation
details and [contracts/field-api.md](./contracts/field-api.md) for full request/response shapes.

## Prerequisites

- Docker + Docker Compose installed
- Repository checked out on branch `001-field-geo-search`

## Setup

```bash
docker compose up -d db      # starts postgis/postgis:16-3.4
alembic upgrade head          # provisions PostGIS extension, field table, GIST index
docker compose up -d web      # starts the FastAPI app
```

## Scenario 1 — Create a valid field (User Story 1, Acceptance Scenario 1)

```bash
curl -s -X POST http://localhost:8000/fields \
  -H "Content-Type: application/json" \
  -d '{
    "name": "North Forty",
    "owner": "Ivan Bondarenko",
    "crop": "wheat",
    "boundary": {
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

**Expected**: `201 Created` with the persisted field, including a generated `id` and `area_ha`
≥ 0.1.

## Scenario 2 — Reject an invalid polygon (User Story 1, Acceptance Scenarios 2–4)

Repeat the request above with:
- an open ring (last point ≠ first point) → expect `422` with a "not closed" message
- a self-crossing ring → expect `422` with a "self-intersect" message
- a tiny ring enclosing < 0.1 ha → expect `422` stating the computed area

**Expected**: no field is created in any case (verify with Scenario 4 below that the fields list is
unchanged).

## Scenario 3 — Find the field by a point inside it (User Story 2, Acceptance Scenario 1)

```bash
curl -s "http://localhost:8000/fields/search?lat=50.4508&lon=30.5242"
```

**Expected**: `200 OK` with `"fields"` containing the field created in Scenario 1.

## Scenario 4 — Search a point outside every field (User Story 2, Acceptance Scenario 2)

```bash
curl -s "http://localhost:8000/fields/search?lat=1.0&lon=1.0"
```

**Expected**: `200 OK` with `"fields": []` — not an error.

## Scenario 5 — Malformed search point (spec Edge Cases)

```bash
curl -s "http://localhost:8000/fields/search?lat=999&lon=30.5"
```

**Expected**: `422 Unprocessable Entity` with an out-of-range coordinate message.

## Running the automated checks

```bash
pytest tests/unit/domain/field            # pure domain validation rules, no services required
pytest tests/integration/infrastructure/field   # spins up an isolated PostGIS container
pytest tests/contract/api/field                 # exercises the endpoints above
```
