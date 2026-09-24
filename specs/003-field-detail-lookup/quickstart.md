# Quickstart: Retrieve a Specific Field

Validates the single user story end-to-end. See [data-model.md](./data-model.md) and
[contracts/field-detail-api.md](./contracts/field-detail-api.md) for details. Assumes
`001-field-geo-search` is already deployed and at least one field exists.

## Prerequisites

- Docker + Docker Compose running (`docker compose up -d db web`)
- At least one field created via `POST /fields` (see `001-field-geo-search` quickstart); note its
  returned `id`

## Scenario 1 — Retrieve an existing field (Acceptance Scenario 1)

```bash
curl -s "http://localhost:8000/fields/<existing-field-id>"
```

**Expected**: `200 OK` with the field's full details (name, owner, crop, boundary, area_ha,
created_at), matching what was returned at creation.

## Scenario 2 — Retrieve a non-existent field (Acceptance Scenario 2)

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "http://localhost:8000/fields/00000000-0000-0000-0000-000000000000"
```

**Expected**: `404 Not Found` with a "no field found" message — not a `200` with empty/null
content.

## Scenario 3 — Malformed identifier (Acceptance Scenario 3)

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/fields/not-a-uuid"
```

**Expected**: `422 Unprocessable Entity` — distinct from the `404` in Scenario 2.

## Scenario 4 — Idempotent retrieval (Edge Case)

```bash
curl -s "http://localhost:8000/fields/<existing-field-id>"
curl -s "http://localhost:8000/fields/<existing-field-id>"
```

**Expected**: Both responses are identical (no side effects from retrieval).

## Running the automated checks

```bash
pytest tests/unit/application/field           # GetFieldByIdUseCase not-found behavior
pytest tests/integration/infrastructure/field  # find_by_id hit/miss, isolated PostGIS
pytest tests/contract/api/field                # GET /fields/{field_id} contract tests
```
