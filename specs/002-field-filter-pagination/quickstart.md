# Quickstart: Field List Filtering & Pagination

Validates all three user stories end-to-end. See [data-model.md](./data-model.md) for
entity/validation details and [contracts/field-filter-api.md](./contracts/field-filter-api.md) for
the full request/response shape. Assumes `001-field-geo-search` is already deployed and some
fields already exist (this feature only reads existing data).

## Prerequisites

- Docker + Docker Compose running (`docker compose up -d db web`, per `001-field-geo-search`)
- The new `area_ha` migration applied: `alembic upgrade head`
- At least a few fields created via `POST /fields` (see `001-field-geo-search` quickstart), with
  varying crops, owners, and areas

## Scenario 1 — Paginate the full list (User Story 1)

```bash
curl -s "http://localhost:8000/fields?page=1&page_size=5"
```

**Expected**: `200 OK`, `items` has at most 5 entries, `page=1`, `page_size=5`, `total_items` and
`total_pages` reflect the full unfiltered field count.

## Scenario 2 — Request a page beyond the last one (User Story 1, Acceptance Scenario 3)

```bash
curl -s "http://localhost:8000/fields?page=9999&page_size=20"
```

**Expected**: `200 OK` with `"items": []` and accurate `total_items`/`total_pages` — not an error.

## Scenario 3 — Filter by crop and owner together (User Story 2)

```bash
curl -s "http://localhost:8000/fields?crop=wheat&owner=ivan"
```

**Expected**: `200 OK` with only fields whose crop is "wheat" (case-insensitive) AND whose owner
name contains "ivan" (case-insensitive).

## Scenario 4 — Filter by area range (User Story 3)

```bash
curl -s "http://localhost:8000/fields?min_area_ha=0.5&max_area_ha=2.0"
```

**Expected**: `200 OK` with only fields whose `area_ha` is between 0.5 and 2.0 inclusive.

## Scenario 5 — Invalid area range (User Story 3, Acceptance Scenario 4)

```bash
curl -s "http://localhost:8000/fields?min_area_ha=5&max_area_ha=1"
```

**Expected**: `422 Unprocessable Entity` stating the minimum exceeds the maximum.

## Scenario 6 — Invalid pagination parameters (Edge Cases)

```bash
curl -s "http://localhost:8000/fields?page=0"
curl -s "http://localhost:8000/fields?page_size=500"
```

**Expected**: both return `422 Unprocessable Entity` — the first for an invalid page number, the
second for exceeding the maximum page size.

## Running the automated checks

```bash
pytest tests/unit/domain/field           # FieldFilter / PageRequest validation, no DB
pytest tests/integration/infrastructure/field  # find_page filtering/pagination, isolated PostGIS
pytest tests/contract/api/field               # GET /fields contract tests
```
