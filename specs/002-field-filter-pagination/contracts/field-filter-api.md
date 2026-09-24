# API Contract: Field List Filtering & Pagination

One REST endpoint, extending `presentation/api/field_router.py` from `001-field-geo-search`.

## GET /fields

Lists fields, optionally filtered by crop, owner, and/or area range, with paginated results. Maps
to User Story 1 (FR-001–FR-005), User Story 2 (FR-006, FR-007, FR-009, FR-011, FR-012), and User
Story 3 (FR-008–FR-010).

### Request

Query parameters (all optional):

| Parameter | Type | Rule |
|---|---|---|
| `crop` | string | Exact match, case-insensitive (FR-006). |
| `owner` | string | Substring match, case-insensitive (FR-007). |
| `min_area_ha` | number | Inclusive lower bound, hectares (FR-008). |
| `max_area_ha` | number | Inclusive upper bound, hectares (FR-008). |
| `page` | integer | ≥ 1. Default `1` (FR-002, FR-013). |
| `page_size` | integer | 1–100. Default `20` (FR-003, FR-013). |

### Response — 200 OK

```json
{
  "items": [
    {
      "id": "b3f1c2a0-...-uuid",
      "name": "North Forty",
      "owner": "Ivan Bondarenko",
      "crop": "wheat",
      "area_ha": 0.87,
      "boundary": { "type": "Polygon", "coordinates": [ ["..."] ] }
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 137,
  "total_pages": 7
}
```

- Empty matches (no fields satisfy the filters, or the page is beyond the last one) return `200`
  with `"items": []` and accurate `total_items`/`total_pages` — never an error (FR-005, FR-011).
- Omitting every filter returns the full field list, paged normally (FR-012).
- Multiple filters are combined with AND (FR-009): e.g. `?crop=wheat&owner=ivan` returns only
  fields matching both.

### Error Responses — 422 Unprocessable Entity

| Condition | Domain Exception | Body `detail` |
|---|---|---|
| `min_area_ha` > `max_area_ha` | `InvalidAreaRangeError` | "Minimum area {min} ha is greater than maximum area {max} ha." |
| `page` < 1 | `InvalidPageRequestError` | "Page must be 1 or greater." |
| `page_size` < 1 or > 100 | `InvalidPageRequestError` | "Page size must be between 1 and 100." |
