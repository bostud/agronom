# Feature Specification: Agricultural Field Management & Point-Based Search

**Feature Branch**: `001-field-geo-search`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "Managing agricultural fields, featuring the ability to quickly search for fields based on point coordinates. Includes creating a new field with name, owner, crop and geometry; polygon must have a minimum area of 0.1ha, and must be closed and non-self-intersecting."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register a New Field (Priority: P1)

An agronomist records a new field by giving it a name, an owner, the crop grown on it, and its
boundary as a polygon drawn or entered on a map. This is the foundational record every other
capability (including search) depends on.

**Why this priority**: Without the ability to create a field with a valid boundary, there is
nothing to search for. This is the minimum viable slice of the feature.

**Independent Test**: Can be fully tested by submitting a field with a name, owner, crop, and a
valid closed polygon, and confirming the field is saved and retrievable with all its attributes
intact.

**Acceptance Scenarios**:

1. **Given** a user filling out a new field form, **When** they submit a name, owner, crop, and a
   closed, non-self-intersecting polygon with an enclosed area of 0.1 hectares or more, **Then**
   the field is created and becomes available for later retrieval and search.
2. **Given** a user submitting a new field, **When** the supplied polygon is not closed (start and
   end points do not match), **Then** the system rejects the submission with a clear validation
   error and creates no field.
3. **Given** a user submitting a new field, **When** the supplied polygon's edges self-intersect,
   **Then** the system rejects the submission with a clear validation error and creates no field.
4. **Given** a user submitting a new field, **When** the enclosed area of the polygon is smaller
   than 0.1 hectares, **Then** the system rejects the submission with a clear validation error
   stating the minimum area requirement and creates no field.
5. **Given** a user submitting a new field, **When** any of name, owner, crop, or geometry is
   missing, **Then** the system rejects the submission with a clear validation error identifying
   the missing field(s).

---

### User Story 2 - Find Fields at a Point (Priority: P2)

A user supplies a single coordinate (for example, by tapping a location on a map) and the system
quickly returns the field(s) whose boundary contains that point, so the user can identify which
field they are looking at without knowing its name in advance.

**Why this priority**: Point-based search is the feature's headline capability, but it is only
valuable once fields with real boundaries exist (User Story 1). It is the second slice because it
builds directly on the data created in Story 1.

**Independent Test**: Can be fully tested by creating one or more fields with known boundaries,
submitting a coordinate known to fall inside one field's boundary, and confirming that exact field
is returned; and submitting a coordinate outside all boundaries, confirming an empty result.

**Acceptance Scenarios**:

1. **Given** at least one field exists with a known boundary, **When** a user searches using a
   coordinate that falls inside that boundary, **Then** the system returns that field.
2. **Given** at least one field exists, **When** a user searches using a coordinate that falls
   outside every field's boundary, **Then** the system returns an empty result rather than an
   error.
3. **Given** two fields with overlapping boundaries both exist, **When** a user searches using a
   coordinate that falls inside both boundaries, **Then** the system returns all fields whose
   boundary contains that point.
4. **Given** a user searches using a coordinate that falls exactly on a field's boundary edge,
   **Then** the system consistently includes or excludes that field (the same input always
   produces the same result).

---

### Edge Cases

- What happens when a polygon is submitted with fewer than 3 distinct vertices (cannot enclose an
  area)? System MUST reject it as an invalid geometry.
- What happens when the search coordinate is missing or malformed (e.g., out-of-range latitude or
  longitude)? System MUST reject the search request with a clear validation error rather than
  silently returning no results.
- How does the system handle a field creation request where the polygon is technically closed and
  non-self-intersecting but has an enclosed area only marginally below 0.1 hectares (e.g., due to
  rounding)? The 0.1 hectare threshold MUST be applied consistently and the rejection message MUST
  state the computed area so the user understands why it was rejected.
- What happens when a field's owner value refers to an owner that does not otherwise exist in the
  system? Owner is treated as a descriptive attribute of the field for this feature; no separate
  owner registry is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a user to create a new field by supplying a name, an owner, a
  crop, and a boundary geometry.
- **FR-002**: System MUST require the boundary geometry to be a closed polygon (its first and last
  points coincide) and MUST reject submissions where it is not closed.
- **FR-003**: System MUST reject boundary geometries whose edges self-intersect.
- **FR-004**: System MUST compute the enclosed area of the boundary geometry and MUST reject
  submissions where that area is smaller than 0.1 hectares.
- **FR-005**: System MUST reject a field creation request that is missing name, owner, crop, or
  geometry, identifying which attribute(s) are missing.
- **FR-006**: System MUST persist every successfully created field with its name, owner, crop, and
  boundary geometry so it can be retrieved later.
- **FR-007**: System MUST allow a user to search for fields by supplying a single point
  (coordinate) and MUST return every field whose boundary contains that point.
- **FR-008**: System MUST return an empty result set (not an error) when a search point falls
  inside no field's boundary.
- **FR-009**: System MUST validate that a search point is a well-formed coordinate and MUST reject
  malformed or out-of-range search requests with a clear validation error.
- **FR-010**: System MUST apply point-in-boundary search across all fields in the system
  regardless of owner: a search returns every field (from any owner) whose boundary contains the
  given point, with no ownership-based visibility restriction.

### Key Entities

- **Field**: An agricultural plot of land. Key attributes: name, owner, crop currently grown, and
  a boundary geometry (a closed, non-self-intersecting polygon covering at least 0.1 hectares).
  The boundary is what point-based search matches against.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a valid new field in under 2 minutes from opening the field form to
  confirmation.
- **SC-002**: 100% of field creation attempts with a non-closed, self-intersecting, or
  under-0.1-hectare polygon are rejected with an explanatory message, and 0% of such attempts
  result in a saved field.
- **SC-003**: A point-based search returns matching field(s) in under 1 second for a system
  containing up to 10,000 fields.
- **SC-004**: 95% of users searching by point correctly identify the field they intended on the
  first attempt.

## Assumptions

- Owner is recorded as a descriptive attribute of the field (e.g., a name) rather than requiring
  the owner to already exist as a user account in the system.
- Crop is recorded as a free-text or single-selection value describing what is currently planted;
  crop history/rotation tracking over time is out of scope for this feature.
- Field boundaries may legitimately overlap between different fields (e.g., shared edges or
  disputed/duplicate surveys); the system does not reject overlapping geometries at creation time.
- Coordinates are expressed in standard latitude/longitude (WGS84); no alternate coordinate
  reference systems are required for this feature.
- "Quickly" in the feature description is interpreted as the sub-second search performance target
  captured in SC-003.
