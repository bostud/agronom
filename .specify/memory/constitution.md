<!--
Sync Impact Report
==================
Version change: (none) → 1.0.0
Rationale: Initial ratification. No prior constitution content existed beyond the
unfilled template scaffold, so this is treated as a MINOR/foundational adoption
version 1.0.0 rather than a bump from an existing baseline.

Modified principles: N/A (initial adoption)

Added sections:
  - Core Principles (8 principles, I–VIII)
  - Technology & Architecture Constraints
  - Development Workflow & Quality Gates
  - Governance

Removed sections: N/A

Templates requiring follow-up:
  - .specify/templates/* — not modified by this command per scope guard; recommend
    reviewing plan/spec/tasks templates against the new principles on next use.

Deferred / TODO placeholders:
  - RATIFICATION_DATE set to 2026-09-23 (date of this ratification) as no earlier
    adoption date exists for this project.
-->

# Agronom Constitution

## Core Principles

### I. Domain-Centric Design
The business domain model is the heart of the application. Domain logic MUST reside
strictly inside the `domain/` layer and MUST remain completely isolated from
infrastructure, frameworks, and I/O concerns. No domain module may import from
`application/`, `infrastructure/`, or `presentation/`.

### II. Clean Architecture / Layered Boundaries
The codebase MUST adhere to strict unidirectional dependencies:
- `domain/` (Entities, Value Objects, Domain Events, Repository Interfaces) → depends
  on nothing else in the codebase.
- `application/` (Use Cases, Command/Query Handlers) → depends only on `domain/`.
- `infrastructure/` (DB persistence, external APIs, frameworks) → depends on
  `application/` and `domain/`.
- `presentation/` (FastAPI routes, CLI commands) → depends on `application/`.

A dependency pointing the wrong direction (e.g. `domain/` importing `infrastructure/`,
or `application/` importing `presentation/`) is a constitution violation and MUST be
rejected in review.

### III. Strict Type Hinting
All function signatures, methods, and public attributes MUST include complete Python
type hints and MUST pass `mypy` in strict/compliant mode. Data structures and value
objects MUST be defined with `pydantic` or `attrs`/`dataclasses` rather than untyped
dicts or ad-hoc classes.

### IV. Immutability by Default
Value objects and domain events MUST be immutable (e.g. frozen Pydantic models or
frozen dataclasses). State changes MUST happen explicitly via aggregate root methods —
mutation of value objects or events in place is prohibited.

### V. No Framework Contamination in Domain
Framework-specific decorators, ORM-mapped classes (e.g. SQLAlchemy mapped classes), and
HTTP-layer exceptions are strictly forbidden inside the `domain/` layer. Database
records MUST be translated to and from domain entities via dedicated mappers/adapters
living in `infrastructure/`.

### VI. Repository Abstraction
Data access MUST use the Repository Pattern. The `application/` layer MUST interact
only with abstract repository interfaces defined in `domain/`. Concrete
implementations (e.g. `SqlAlchemyUserRepository`) MUST live in `infrastructure/` and
MUST NOT be imported directly by `application/` or `domain/` code.

### VII. Fail Fast with Explicit Errors
Business logic failures MUST raise explicit, domain-specific exceptions (e.g.
`InsufficientFundsError`, `UserNotFoundError`) rather than being silently swallowed or
mapped to generic catch-all exceptions. Silent fallbacks that mask a business rule
violation are prohibited.

### VIII. Test-First & Fixture Discipline
Unit tests for domain entities and value objects MUST be written independently of any
database or framework — no test database, ORM session, or HTTP client may be required
to exercise `domain/` logic. Integration tests MUST use isolated test containers or
transactional rollbacks so tests do not leak state between runs.

## Technology & Architecture Constraints

Python is the sole implementation language. Type checking via `mypy` and data
modeling via `pydantic` and/or `attrs`/`dataclasses` are required project-wide, not
optional tooling. `FastAPI` is the sanctioned framework for the `presentation/` HTTP
layer; CLI entry points also live in `presentation/`. SQLAlchemy (or an equivalent
ORM) is confined to `infrastructure/` and MUST NOT leak ORM types across the
`application/`↔`infrastructure/` boundary — only mapped domain entities cross that
boundary.

## Development Workflow & Quality Gates

Every pull request MUST be checked against the layering rules in Principle II before
merge; a change that introduces a dependency pointing the wrong direction MUST be
rejected or restructured, not waived. `mypy` and the test suite (domain unit tests plus
integration tests) MUST pass in CI before merge. New business rules MUST land with a
corresponding domain-specific exception type and a unit test asserting it is raised,
per Principles VII and VIII.

## Governance

This constitution supersedes all other development practices and conventions in this
repository. Any conflict between this document and other guidance (READMEs, code
comments, prior habits) is resolved in favor of this constitution.

**Amendment procedure**: Amendments are proposed via a change to
`.specify/memory/constitution.md`, must state the rationale for the change, and take
effect once merged. The `Sync Impact Report` at the top of the file MUST be updated
for every amendment and removed before the amendment is considered final documentation
(it is scratch material for review, not governance content).

**Versioning policy**: This constitution is versioned independently using semantic
versioning:
- MAJOR: Backward-incompatible governance changes, or removal/redefinition of an
  existing principle.
- MINOR: A new principle or section is added, or existing guidance is materially
  expanded.
- PATCH: Clarifications, wording fixes, and non-semantic refinements.

**Compliance review**: All PRs and code reviews MUST verify compliance with the Core
Principles above, in particular the layering rules (Principle II) and the prohibition
on framework contamination in `domain/` (Principle V). Any deviation MUST be justified
in the PR description and, if accepted as a lasting exception, MUST be reflected back
into this constitution via an amendment rather than left as undocumented drift.

**Version**: 1.0.0 | **Ratified**: 2026-09-23 | **Last Amended**: 2026-09-23
