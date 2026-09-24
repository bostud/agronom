---

description: "Task list template for feature implementation"
---

# Tasks: Field List Filtering & Pagination

**Input**: Design documents from `/specs/002-field-filter-pagination/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/field-filter-api.md,
quickstart.md — all extend the `Field` aggregate, `FieldRepository` interface,
`PostgisFieldRepository`, and presentation layer created in `specs/001-field-geo-search`. That
feature's Foundational and User Story tasks must already be implemented.

**Tests**: Included. The project constitution (Principle VIII, "Test-First & Fixture Discipline")
mandates domain unit tests independent of any database/framework, plus integration tests using
isolated containers — consistent with `001-field-geo-search`.

**Organization**: Tasks are grouped by user story. All three stories are served by a single `GET
/fields` endpoint and a single `find_page` repository method (plan.md Summary): US1 delivers that
endpoint with pagination only (an empty filter), US2 and US3 each incrementally extend the same
query builder and endpoint to add their filter predicates, without breaking the prior story's
behavior.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Extends the existing single backend service from `001-field-geo-search`:
`src/domain/`, `src/application/`, `src/infrastructure/`, `src/presentation/`, `tests/unit/`,
`tests/integration/`, `tests/contract/`.

---

## Phase 1: Setup

- [X] T001 Verify prerequisite: confirm `src/domain/field/entities.py`, `src/domain/field/repository.py`,
      `src/infrastructure/field/postgis_repository.py`, `src/infrastructure/field/models.py`, and
      `src/presentation/api/field_router.py` already exist and are working (from
      `specs/001-field-geo-search`) before proceeding — this feature only extends them; no new
      dependencies or services are introduced (plan.md Summary).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain and persistence additions all three user stories share, since they are served
by one `find_page` method and one endpoint

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Create `PageRequest` and `Page[T]` in `src/domain/common/pagination.py` (new
      `domain/common/` module — add `__init__.py`): `PageRequest.page` MUST be ≥ 1 and
      `PageRequest.page_size` MUST be between 1 and 100 inclusive (FR-002, FR-003, FR-013);
      `Page[T]` holds `items`, `page`, `page_size`, `total_items`, and `total_pages` (data-model.md
      Page[T]). Both frozen (constitution Principle IV).
- [X] T003 [P] Add `InvalidAreaRangeError` and `InvalidPageRequestError` to
      `src/domain/field/exceptions.py`, inheriting from the existing `FieldDomainError` base
      (data-model.md Domain Exceptions).
- [X] T004 Add the `FieldFilter` value object to `src/domain/field/value_objects.py` (depends on
      T003): optional `crop`, `owner`, `min_area_ha`, `max_area_ha` (all `None` by default — "an
      empty `FieldFilter` ... represents 'no filtering'", FR-012); raises `InvalidAreaRangeError`
      at construction when both `min_area_ha` and `max_area_ha` are set and
      `min_area_ha > max_area_ha` (FR-010).
- [X] T005 Extend the abstract `FieldRepository` interface in `src/domain/field/repository.py`
      (depends on T002, T004) with
      `find_page(filter: FieldFilter, page_request: PageRequest) -> Page[Field]` (data-model.md
      Repository Interface) — no database logic in this file (constitution Principle I).
- [X] T006 Add a persisted, indexed `area_ha` column (btree index) to `FieldModel` in
      `src/infrastructure/field/models.py`, computed once from the geodesic area already used for
      the 0.1 ha minimum-area rule (research.md Decision 1).
- [X] T007 Create the Alembic migration adding the `area_ha` column and its btree index to the
      `field` table in `migrations/versions/` (depends on T006).
- [X] T008 Update `field_to_model` in `src/infrastructure/field/mappers.py` (depends on T006) to
      populate the new `area_ha` column from `field.area_ha` when persisting.

**Checkpoint**: Foundation ready — User Story 1 implementation can now begin.

---

## Phase 3: User Story 1 - Browse Fields a Page at a Time (Priority: P1) 🎯 MVP

**Goal**: List fields with results returned a page at a time, with accurate total-count/total-page
metadata, and an out-of-range page returning an empty list rather than an error.

**Independent Test**: Create more fields than fit on one page, request the default first page,
confirm the correct number of results plus accurate total-count and total-page metadata; request a
later page and confirm a different, correct subset; request a page beyond the last one and confirm
an empty list with accurate metadata.

### Tests for User Story 1 ⚠️

> **Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US1] Unit test `PageRequest` validation in
      `tests/unit/domain/common/test_pagination.py` (depends on T002): `page < 1` raises
      `InvalidPageRequestError` (FR-013); `page_size < 1` or `page_size > 100` raises
      `InvalidPageRequestError` stating the bound (FR-003); a valid `PageRequest` (e.g. page=1,
      page_size=20) is accepted.
- [X] T010 [P] [US1] Contract test `GET /fields` (pagination only, no filters) in
      `tests/contract/api/field/test_list_fields.py` (per contracts/field-filter-api.md): default
      request returns the first page with the default page size and accurate `total_items`/
      `total_pages` (FR-001, FR-002); an explicit `page`/`page_size` returns exactly that slice
      (Acceptance Scenario 2); a page beyond the last returns `200` with `"items": []` and accurate
      metadata, not an error (FR-005, Acceptance Scenario 3); `page=0` or `page_size=500` returns
      `422` (FR-013).
- [X] T011 [P] [US1] Integration test `PostgisFieldRepository.find_page` (pagination only, empty
      filter) in `tests/integration/infrastructure/field/test_postgis_repository_find_page.py`
      using a testcontainers-provisioned isolated PostGIS instance: seed more fields than one page,
      verify page 1 and page 2 contents, verify `total_items`/`total_pages` accuracy (FR-004), and
      verify a page past the last one returns an empty `items` tuple.

### Implementation for User Story 1

- [X] T012 [US1] Implement `ListFieldsUseCase` in `src/application/field/list_fields.py` (depends
      on T005): accepts a `FieldFilter` and `PageRequest`, delegates to
      `FieldRepository.find_page`, and returns the resulting `Page[Field]` unchanged.
- [X] T013 [US1] Implement `PostgisFieldRepository.find_page` in
      `src/infrastructure/field/postgis_repository.py` (depends on T005, T006, T007, T008): builds
      a query with `LIMIT`/`OFFSET` from `page_request` (no `WHERE` clause yet, since `FieldFilter`
      is empty in this story), plus a `COUNT(*)` for `total_items`, and computes `total_pages` as
      `ceil(total_items / page_size)` (data-model.md Page[T]).
- [X] T014 [US1] Implement the paginated list response DTOs in `src/presentation/api/schemas.py`
      matching the `GET /fields` response shape in contracts/field-filter-api.md (`items`, `page`,
      `page_size`, `total_items`, `total_pages`).
- [X] T015 [US1] Implement the `GET /fields` endpoint in `src/presentation/api/field_router.py`
      (depends on T012, T014): accepts optional `page` (default 1) and `page_size` (default 20)
      query parameters, constructs `PageRequest` (mapping `InvalidPageRequestError` to `422`),
      constructs an empty `FieldFilter` for this story's scope, invokes `ListFieldsUseCase`, and
      returns `200` with the paginated response.

**Checkpoint**: User Story 1 is fully functional and testable independently — plain pagination
works end to end with no filters yet.

---

## Phase 4: User Story 2 - Filter by Crop and Owner (Priority: P2)

**Goal**: Narrow the paginated field list by crop, by owner, or by both together, composing with
the pagination from User Story 1.

**Independent Test**: Create fields with varying crops and owners; filter by crop alone, owner
alone, and both together; confirm only matching fields are returned in each case, still paginated
correctly.

### Tests for User Story 2 ⚠️

- [X] T016 [P] [US2] Unit test `FieldFilter` crop/owner construction in
      `tests/unit/domain/field/test_value_objects.py` (depends on T004): a `FieldFilter` with only
      `crop` set is valid; with only `owner` set is valid; with both set is valid.
- [X] T017 [P] [US2] Contract test `GET /fields?crop=&owner=` in
      `tests/contract/api/field/test_list_fields.py` (extends T010's file): filtering by `crop`
      alone returns only fields with that crop, case-insensitively (FR-006, Acceptance Scenario 1);
      filtering by `owner` alone returns only fields whose owner matches, case-insensitively as a
      substring (FR-007, Acceptance Scenario 2); supplying both returns only fields matching both
      (FR-009, Acceptance Scenario 3); a filter matching no field returns `200` with `"items": []`
      (FR-011, Acceptance Scenario 4).
- [X] T018 [P] [US2] Integration test `PostgisFieldRepository.find_page` crop/owner filtering in
      `tests/integration/infrastructure/field/test_postgis_repository_find_page.py` (extends
      T011's file): case-insensitive exact crop match; case-insensitive substring owner match;
      both filters combined with AND.

### Implementation for User Story 2

- [X] T019 [US2] Extend the query builder inside `PostgisFieldRepository.find_page` in
      `src/infrastructure/field/postgis_repository.py` (depends on T013) to add a case-insensitive
      exact-match `WHERE` clause for `crop` when `FieldFilter.crop` is set (research.md Decision
      3), and a case-insensitive substring (`ILIKE`) `WHERE` clause for `owner` when
      `FieldFilter.owner` is set (research.md Decision 4).
- [X] T020 [US2] Extend the `GET /fields` endpoint in `src/presentation/api/field_router.py`
      (depends on T015, T019) to accept optional `crop` and `owner` query parameters and pass them
      into the `FieldFilter` constructed for the request.

**Checkpoint**: User Stories 1 and 2 both work independently and together — crop/owner filtering
composes with pagination.

---

## Phase 5: User Story 3 - Filter by Area Range (Priority: P3)

**Goal**: Narrow the paginated, optionally crop/owner-filtered field list to fields whose area
falls within a minimum, a maximum, or both bounds.

**Independent Test**: Create fields with varying areas; filter with only a minimum, only a
maximum, and both together; confirm only fields within range are returned; confirm an inverted
range (min > max) is rejected.

### Tests for User Story 3 ⚠️

- [X] T021 [P] [US3] Unit test `FieldFilter` area-range validation in
      `tests/unit/domain/field/test_value_objects.py` (extends T016's file, depends on T004):
      `min_area_ha > max_area_ha` raises `InvalidAreaRangeError` (FR-010); `min_area_ha` alone is
      valid; `max_area_ha` alone is valid; both set with `min_area_ha <= max_area_ha` is valid.
- [X] T022 [P] [US3] Contract test `GET /fields?min_area_ha=&max_area_ha=` in
      `tests/contract/api/field/test_list_fields.py` (extends T017's file): only `min_area_ha`
      returns fields with area at or above it (FR-008, Acceptance Scenario 1); only `max_area_ha`
      returns fields with area at or below it (Acceptance Scenario 2); both together return fields
      in that inclusive range (Acceptance Scenario 3); `min_area_ha > max_area_ha` returns `422`
      with no results (FR-010, Acceptance Scenario 4); an area filter combined with `crop`/`owner`
      returns only fields matching every supplied filter (Acceptance Scenario 5).
- [X] T023 [P] [US3] Integration test `PostgisFieldRepository.find_page` area-range filtering in
      `tests/integration/infrastructure/field/test_postgis_repository_find_page.py` (extends
      T018's file): verifies inclusive `min_area_ha`/`max_area_ha` bounds against the persisted,
      indexed `area_ha` column.

### Implementation for User Story 3

- [X] T024 [US3] Extend the query builder inside `PostgisFieldRepository.find_page` in
      `src/infrastructure/field/postgis_repository.py` (depends on T019) to add
      `area_ha >= min_area_ha` and/or `area_ha <= max_area_ha` `WHERE` clauses when
      `FieldFilter.min_area_ha`/`max_area_ha` are set.
- [X] T025 [US3] Extend the `GET /fields` endpoint in `src/presentation/api/field_router.py`
      (depends on T020, T024) to accept optional `min_area_ha` and `max_area_ha` query parameters,
      completing the `FieldFilter` constructed for the request, and mapping
      `InvalidAreaRangeError` to a `422` response with the exact detail message from
      contracts/field-filter-api.md.

**Checkpoint**: All three user stories work independently and together in one composable `GET
/fields` endpoint.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 [P] Run all quickstart.md scenarios (1–6) end-to-end against the docker-compose
      environment and confirm each matches its documented expected outcome.
- [X] T027 [P] Run `mypy` across `src/` in strict mode and resolve any typing errors introduced by
      this feature (constitution Principle III).
- [X] T028 Audit `src/domain/common/pagination.py` and the `FieldFilter`/exception additions in
      `src/domain/field/` to confirm zero imports from `application/`, `infrastructure/`,
      `presentation/`, or any ORM/HTTP/framework module (constitution Principles I, II, V).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Depends on `001-field-geo-search` already being implemented (T001 verifies
  this) — can start immediately once that's confirmed.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all three user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion only.
- **User Story 2 (Phase 4)**: Depends on User Story 1's `find_page`/endpoint existing (T013, T015)
  — it extends the same query builder and endpoint rather than starting fresh, per plan.md's
  "one method serves all of them."
- **User Story 3 (Phase 5)**: Depends on User Story 2's extensions (T019, T020) for the same
  reason.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests MUST be written and FAIL before their corresponding implementation tasks.
- Foundational value objects/exceptions (T002–T005) before any repository or use-case work.
- Repository method (T013, extended by T019, T024) before the endpoint that calls it (T015,
  extended by T020, T025).
- Use case (T012) before the endpoint (T015).

### Parallel Opportunities

- Foundational tasks T002 and T003 can run in parallel (different files).
- Within US1: T009, T010, T011 can all run in parallel (different files).
- Within US2: T016, T017, T018 can all run in parallel (different files).
- Within US3: T021, T022, T023 can all run in parallel (different files).
- Polish tasks T026 and T027 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test PageRequest validation in tests/unit/domain/common/test_pagination.py"
Task: "Contract test GET /fields (pagination only) in tests/contract/api/field/test_list_fields.py"
Task: "Integration test PostgisFieldRepository.find_page (pagination only) in tests/integration/infrastructure/field/test_postgis_repository_find_page.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify `001-field-geo-search` is in place).
2. Complete Phase 2: Foundational (CRITICAL — blocks all three stories).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run T009–T011 and quickstart.md Scenarios 1–2.
5. Deploy/demo if ready — plain pagination over the full field list is a usable increment on its
   own.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. Add User Story 1 → validate independently → deploy/demo (MVP: pagination only).
3. Add User Story 2 → validate independently (quickstart Scenario 3) → deploy/demo (crop/owner
   filtering).
4. Add User Story 3 → validate independently (quickstart Scenarios 4–5) → deploy/demo (area-range
   filtering, fully composable).
5. Polish (Phase 6) once all three stories are complete.
