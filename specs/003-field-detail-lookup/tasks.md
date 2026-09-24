---

description: "Task list template for feature implementation"
---

# Tasks: Retrieve a Specific Field

**Input**: Design documents from `/specs/003-field-detail-lookup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/field-detail-api.md,
quickstart.md — all extend the `Field` aggregate, `FieldRepository` interface,
`PostgisFieldRepository`, and `FieldResponse` DTO created in `specs/001-field-geo-search`. That
feature's Foundational tasks (T006–T012) must exist before this feature's tasks can proceed.

**Tests**: Included. The project constitution (Principle VIII, "Test-First & Fixture Discipline")
mandates domain/application unit tests independent of any database/framework, plus integration
tests using isolated containers — consistent with `001-field-geo-search` and
`002-field-filter-pagination`.

**Organization**: This feature has a single user story (US1 = Retrieve a Field by Identifier), so
there is one implementation phase after the shared foundational extensions.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Include exact file paths in descriptions

## Path Conventions

Extends the existing single backend service from `001-field-geo-search`:
`src/domain/`, `src/application/`, `src/infrastructure/`, `src/presentation/`, `tests/unit/`,
`tests/integration/`, `tests/contract/`.

---

## Phase 1: Setup

- [X] T001 Verify prerequisite: confirm `src/domain/field/entities.py`, `src/domain/field/repository.py`,
      `src/infrastructure/field/postgis_repository.py`, and the `FieldResponse` DTO in
      `src/presentation/api/schemas.py` already exist (from `specs/001-field-geo-search`) before
      proceeding — this feature only extends them; no new dependencies or services are introduced
      (plan.md Summary).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain additions this feature's single user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add `FieldNotFoundError` in `src/domain/field/exceptions.py` (depends on T001):
      inherits from the existing `FieldDomainError` base; represents "no field exists with the
      specified identifier" (FR-003) — see data-model.md Domain Exceptions.
- [X] T003 Extend the abstract `FieldRepository` interface in `src/domain/field/repository.py`
      (depends on T001) with `find_by_id(field_id: UUID) -> Field | None` (data-model.md
      Repository Interface) — no database logic in this file (constitution Principle I).

**Checkpoint**: Foundation ready — User Story 1 implementation can now begin.

---

## Phase 3: User Story 1 - Retrieve a Field by Identifier (Priority: P1) 🎯 MVP

**Goal**: Given a field's identifier, return its full details, or a clear "not found" result if no
field with that identifier exists.

**Independent Test**: Create a field, retrieve it by its identifier, and confirm its full stored
details are returned exactly; request an identifier that does not correspond to any field and
confirm a clear "not found" result rather than an error or a false-positive empty success.

### Tests for User Story 1 ⚠️

> **Write these tests FIRST, ensure they FAIL before implementation**

- [X] T004 [P] [US1] Unit test `GetFieldByIdUseCase` in
      `tests/unit/application/field/test_get_field_by_id.py` (depends on T002, T003) using a
      fake/in-memory `FieldRepository`: when the repository returns `None`, the use case raises
      `FieldNotFoundError` (FR-003); when the repository returns a `Field`, the use case returns
      that same `Field` unchanged (FR-002, FR-005 — no side effects).
- [X] T005 [P] [US1] Contract test `GET /fields/{field_id}` in
      `tests/contract/api/field/test_get_field.py` (per contracts/field-detail-api.md): an
      existing field's ID returns `200` with full details (name, owner, crop, boundary, area_ha,
      created_at) matching what was created (FR-002); a syntactically valid but non-existent UUID
      returns `404` (FR-003); a malformed identifier returns `422`, distinct from the `404` case
      (FR-004).
- [X] T006 [P] [US1] Integration test `PostgisFieldRepository.find_by_id` in
      `tests/integration/infrastructure/field/test_postgis_repository_find_by_id.py` using a
      testcontainers-provisioned isolated PostGIS instance: an existing field's ID returns that
      exact `Field`; a random, non-existent UUID returns `None`.

### Implementation for User Story 1

- [X] T007 [US1] Implement `GetFieldByIdUseCase` in `src/application/field/get_field_by_id.py`
      (depends on T002, T003): calls `FieldRepository.find_by_id`, raises `FieldNotFoundError`
      when it returns `None` (FR-003), and otherwise returns the found `Field` unchanged (FR-002).
- [X] T008 [US1] Implement `PostgisFieldRepository.find_by_id` in
      `src/infrastructure/field/postgis_repository.py` (depends on T003): an indexed primary-key
      lookup returning `None` when no row matches, mapped to a domain `Field` via the existing
      mapper when found.
- [X] T009 [US1] Implement the `GET /fields/{field_id}` endpoint in
      `src/presentation/api/field_router.py` (depends on T007): declares `field_id` as a `UUID`
      path parameter so malformed values are rejected automatically with `422` (FR-004,
      research.md Decision 1); invokes `GetFieldByIdUseCase`; maps `FieldNotFoundError` to a `404`
      response with the exact detail message from contracts/field-detail-api.md; returns `200`
      with the existing `FieldResponse` DTO on success (research.md Decision 3 — no new DTO).

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T010 [P] Run all quickstart.md scenarios (1–4) end-to-end against the docker-compose
      environment and confirm each matches its documented expected outcome.
- [X] T011 [P] Run `mypy` across `src/` in strict mode and resolve any typing errors introduced by
      this feature (constitution Principle III).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Depends on `001-field-geo-search` already being implemented (T001 verifies
  this) — can start immediately once that's confirmed.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS User Story 1.
- **User Story 1 (Phase 3)**: Depends on Foundational completion only.
- **Polish (Phase 4)**: Depends on User Story 1 being complete.

### Within User Story 1

- Tests (T004–T006) MUST be written and FAIL before their corresponding implementation tasks.
- Repository interface extension (T003) before its implementation (T008).
- Domain exception (T002) and repository extension (T003) before the use case (T007).
- Use case (T007) and repository implementation (T008) before the endpoint (T009).

### Parallel Opportunities

- Foundational tasks T002 and T003 can run in parallel (different files).
- Within US1: T004, T005, T006 can all run in parallel (different files, no dependency between
  them).
- Polish tasks T010 and T011 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test GetFieldByIdUseCase in tests/unit/application/field/test_get_field_by_id.py"
Task: "Contract test GET /fields/{field_id} in tests/contract/api/field/test_get_field.py"
Task: "Integration test PostgisFieldRepository.find_by_id in tests/integration/infrastructure/field/test_postgis_repository_find_by_id.py"
```

---

## Implementation Strategy

### MVP First (and Only) Scope

1. Complete Phase 1: Setup (verify `001-field-geo-search` is in place).
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run T004–T006 and quickstart.md Scenarios 1–4.
5. Deploy/demo — this feature is complete once US1 is done; there is no further increment.
