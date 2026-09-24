# API Contract: Retrieve a Specific Field

One REST endpoint, extending `presentation/api/field_router.py` from `001-field-geo-search`.

## GET /fields/{field_id}

Retrieves a single field by its identifier. Maps to User Story 1 (FR-001–FR-005).

### Request

Path parameter:

| Parameter | Type | Rule |
|---|---|---|
| `field_id` | UUID | Required. A syntactically invalid value is rejected before reaching application code (FR-004). |

### Response — 200 OK

Same shape as the existing `FieldResponse` from `001-field-geo-search`'s `POST /fields`:

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

### Error Responses

| Condition | Status | Domain Exception | Body `detail` |
|---|---|---|---|
| No field exists with `field_id` | `404 Not Found` | `FieldNotFoundError` | "No field found with id {field_id}." |
| `field_id` is not a valid UUID | `422 Unprocessable Entity` | — (rejected at the presentation boundary before use case invocation, per research.md Decision 1) | Standard FastAPI path-parameter validation error. |
