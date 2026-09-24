# API Contract: Field Management & Point-Based Search

Two REST endpoints, exposed by `presentation/api/field_router.py`. Request/response bodies are
JSON. Coordinates use `[longitude, latitude]` ordering for polygon rings (GeoJSON convention) and
separate `lat`/`lon` query parameters for point search.

## POST /fields

Creates a new field. Maps to User Story 1 (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006).

### Request

```json
{
  "name": "North Forty",
  "owner": "Ivan Bondarenko",
  "crop": "wheat",
  "boundary": {
    "type": "Polygon",
    "coordinates": [
      [
        [30.5234, 50.4501],
        [30.5250, 50.4501],
        [30.5250, 50.4515],
        [30.5234, 50.4515],
        [30.5234, 50.4501]
      ]
    ]
  }
}
```

### Response — 201 Created

```json
{
  "id": "b3f1c2a0-...-uuid",
  "name": "North Forty",
  "owner": "Ivan Bondarenko",
  "crop": "wheat",
  "boundary": { "type": "Polygon", "coordinates": [ ["..."] ] },
  "area_ha": 0.87,
  "created_at": "2026-09-23T12:00:00Z"
}
```

### Error Responses — 422 Unprocessable Entity

| Condition | Domain Exception | Body `detail` |
|---|---|---|
| Boundary not closed | `PolygonNotClosedError` | "Polygon boundary is not closed: first and last points do not match." |
| Boundary self-intersects | `SelfIntersectingPolygonError` | "Polygon boundary edges self-intersect." |
| Area below threshold | `PolygonTooSmallError` | "Polygon area is {computed} ha, below the required minimum of 0.1 ha." |
| Fewer than 3 vertices | `PolygonNotClosedError` / geometry error | "Polygon must have at least 3 distinct vertices." |
| Missing `name`/`owner`/`crop`/`boundary` | `MissingFieldAttributeError` | "Missing required field(s): {attribute names}." |

Each error case corresponds directly to spec.md Acceptance Scenarios 2–5 under User Story 1 and
the "fewer than 3 vertices" Edge Case — no field is created in any of these cases (SC-002).

## GET /fields/search?lat={lat}&lon={lon}

Finds all fields whose boundary contains the given point. Maps to User Story 2 (FR-007, FR-008,
FR-009).

### Request

Query parameters:
- `lat` (float, required) — latitude, -90.0 to 90.0
- `lon` (float, required) — longitude, -180.0 to 180.0

### Response — 200 OK

```json
{
  "fields": [
    {
      "id": "b3f1c2a0-...-uuid",
      "name": "North Forty",
      "owner": "Ivan Bondarenko",
      "crop": "wheat",
      "boundary": { "type": "Polygon", "coordinates": [ ["..."] ] }
    }
  ]
}
```

- If the point falls inside no field's boundary, response is `200 OK` with `"fields": []` — never
  an error (FR-008, Acceptance Scenario 2).
- If the point falls inside multiple overlapping boundaries, every matching field is included
  (Acceptance Scenario 3).
- A point exactly on a boundary edge is handled consistently (same input always yields the same
  result) per Acceptance Scenario 4 — determined by the underlying `ST_Contains` semantics
  (boundary-inclusive containment).

### Error Responses — 422 Unprocessable Entity

| Condition | Domain Exception | Body `detail` |
|---|---|---|
| `lat`/`lon` missing or out of range | `InvalidCoordinateError` | "Invalid coordinate: latitude/longitude out of range or missing." |
