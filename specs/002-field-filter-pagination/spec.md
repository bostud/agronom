# Feature Specification: Field List Filtering & Pagination

**Feature Branch**: `002-field-filter-pagination`

**Created**: 2026-09-24

**Status**: Draft

**Input**: User description: "Implement fields filter resource by crop, owner, min-max area with results pagination."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Fields a Page at a Time (Priority: P1)

A user viewing the list of registered fields receives results a page at a time instead of the
entire dataset at once, so the list stays usable as the number of fields grows.

**Why this priority**: Pagination is the foundation every filter builds on — without it, a filtered
list is just as unusable as the unfiltered one once the field count is large. It is also useful on
its own before any filter is applied.

**Independent Test**: Can be fully tested by creating more fields than fit on one page, requesting
the default first page, confirming the correct number of results plus accurate total-count and
total-page metadata, then requesting a later page and confirming a different, correct subset.

**Acceptance Scenarios**:

1. **Given** more fields exist than the default page size, **When** a user requests the field list
   with no page specified, **Then** the first page is returned with the default number of results,
   along with the total number of matching fields and total number of pages.
2. **Given** a user specifies a page number and page size, **When** they request the list,
   **Then** exactly that slice of results is returned.
3. **Given** a user requests a page number beyond the last available page, **When** they request
   it, **Then** an empty result list is returned — not an error — with accurate metadata.

---

### User Story 2 - Filter by Crop and Owner (Priority: P2)

A user narrows the field list down to a specific crop, a specific owner, or both, so they can find
relevant fields without scanning the entire list.

**Why this priority**: These are the two most identity-defining filters named in the feature
request, and they build directly on the paginated list from User Story 1.

**Independent Test**: Can be fully tested by creating fields with varying crops and owners, then
filtering by crop alone, owner alone, and both together, confirming only matching fields are
returned in each case.

**Acceptance Scenarios**:

1. **Given** fields with different crops exist, **When** a user filters by a specific crop,
   **Then** only fields growing that crop are returned.
2. **Given** fields with different owners exist, **When** a user filters by owner, **Then** only
   fields belonging to that owner are returned.
3. **Given** both a crop filter and an owner filter are supplied together, **When** the user
   requests the list, **Then** only fields matching both filters are returned.
4. **Given** a crop or owner filter that matches no field, **When** the user requests the list,
   **Then** an empty result list is returned — not an error.

---

### User Story 3 - Filter by Area Range (Priority: P3)

A user narrows the field list to fields whose area falls within a minimum, a maximum, or both
bounds, so they can find fields of a particular size.

**Why this priority**: Area filtering is the least central of the three filters named in the
feature request and composes with, but does not depend on, User Story 2's filters.

**Independent Test**: Can be fully tested by creating fields with varying areas, then filtering
with only a minimum, only a maximum, and both together, confirming only fields within range are
returned.

**Acceptance Scenarios**:

1. **Given** fields with varying areas exist, **When** a user filters with only a minimum area,
   **Then** only fields with area at or above that minimum are returned.
2. **Given** fields with varying areas exist, **When** a user filters with only a maximum area,
   **Then** only fields with area at or below that maximum are returned.
3. **Given** both a minimum and a maximum area are supplied, **When** the user requests the list,
   **Then** only fields whose area falls within that inclusive range are returned.
4. **Given** a minimum area greater than the supplied maximum area, **When** the user requests the
   list, **Then** the request is rejected with a clear validation error and no results are
   returned.
5. **Given** an area filter is combined with a crop and/or owner filter, **When** the user requests
   the list, **Then** only fields matching every supplied filter are returned.

---

### Edge Cases

- What happens when the requested page number is zero, negative, or otherwise not a valid page
  index? System MUST reject the request with a clear validation error rather than silently
  defaulting.
- What happens when the requested page size is zero, negative, or exceeds the maximum allowed page
  size? System MUST reject the request with a clear validation error stating the maximum allowed
  page size.
- What happens when a crop or owner filter value does not match any existing field (e.g. a typo)?
  System MUST return a successful empty result, not an error.
- What happens when no filters are supplied at all? System MUST return the full field list, paged
  normally.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a way to list fields with results returned a page at a time
  rather than all at once.
- **FR-002**: System MUST allow the caller to specify which page of results to retrieve, defaulting
  to the first page when not specified.
- **FR-003**: System MUST allow the caller to specify how many results appear per page, defaulting
  to a standard page size when not specified, and MUST reject requests specifying a page size above
  the maximum allowed, stating that maximum in the error.
- **FR-004**: Every paginated response MUST include the total number of matching fields and the
  total number of pages available.
- **FR-005**: A request for a page beyond the last available page MUST return an empty result list,
  not an error.
- **FR-006**: System MUST allow filtering the field list by crop.
- **FR-007**: System MUST allow filtering the field list by owner.
- **FR-008**: System MUST allow filtering the field list by a minimum area, a maximum area, or
  both.
- **FR-009**: When more than one filter is supplied at once, System MUST return only fields that
  satisfy every supplied filter.
- **FR-010**: System MUST reject a request where the supplied minimum area is greater than the
  supplied maximum area, with a clear validation error, and MUST return no results in that case.
- **FR-011**: A filter combination that matches no fields MUST return a successful empty result
  (with accurate pagination metadata), not an error.
- **FR-012**: All filters MUST be optional; a request with no filters MUST return the full,
  paginated field list.
- **FR-013**: System MUST reject a request specifying an invalid (non-positive) page number or page
  size with a clear validation error.

### Key Entities

- **Field**: The existing agricultural field record (name, owner, crop, boundary/area — see the
  field management feature). This feature reads and filters existing `Field` records; it does not
  add new attributes to them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can retrieve any page of the (optionally filtered) field list in under 1
  second for a system containing up to 10,000 fields.
- **SC-002**: 100% of paginated responses include a total result count and total page count that
  exactly match the underlying filtered data set.
- **SC-003**: 100% of requests combining crop, owner, and/or area-range filters return only fields
  matching every specified filter, with zero false positives.
- **SC-004**: 100% of requests with an invalid area range (minimum greater than maximum) or an
  invalid page number/size are rejected with an explanatory error and return no results.

## Assumptions

- Multiple filters supplied together combine with logical AND (a result must satisfy every
  supplied filter), not OR.
- The crop filter matches on the field's exact crop value (case-insensitive); crop values are
  treated as a bounded/categorical field in practice.
- The owner filter matches on a case-insensitive partial (substring) match against the owner name,
  since owner is a free-text name a user may only partially remember.
- Minimum and maximum area bounds are both optional and independent (a caller may supply just one),
  and are inclusive of the boundary value itself, expressed in hectares (consistent with the
  existing 0.1 ha minimum field size rule).
- Pagination defaults to a standard page size of 20 results with a maximum allowed page size of
  100; results are returned in a stable default order (by field name, ascending) when no explicit
  sort is requested.
- This feature is read-only: it lists and filters existing fields and does not create, modify, or
  delete them.
