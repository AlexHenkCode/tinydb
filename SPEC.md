# SPEC: Unique Field Constraint

## Goal

Add support for unique field constraints to TinyDB tables.

Example:

    table = db.table('users')
    table.add_unique('email')

After registration, the table must reject writes
that introduce duplicate values in the email field.

## Scope

Implement:

    Table.add_unique(field: str)

The constraint applies independently to each table.

## Functional Requirements

### FR-01: Register Constraint

- add_unique(field) registers a unique constraint.
- field must be a non-empty string.
- Multiple unique constraints can exist on one table.
- Registering the same constraint twice is idempotent.
- Registration validates existing documents.
- If existing documents contain duplicates, raise ValueError.
- A failed registration must not activate the constraint.

### FR-02: Insert

Reject insertion if the new document introduces
a duplicate value in a constrained field.

### FR-03: Insert Multiple

- Validate all documents in the batch.
- Detect duplicates between existing and incoming documents.
- Detect duplicates within the incoming batch.
- Reject the entire operation if a conflict exists.

### FR-04: Update

Enforce constraints when using:

- update(mapping, cond)
- update(mapping, doc_ids)
- update(callable, cond)
- update(callable, doc_ids)
- update(mapping) without filters

Updates must be validated against the resulting table state.

### FR-05: Update Multiple

Enforce all active constraints after applying
the requested update operations.

### FR-06: Upsert

Enforce constraints both when updating existing
documents and when inserting new documents.

### FR-07: Remove

Removing documents must not violate unique constraints.

## Constraint Semantics

- Uniqueness is scoped to one table.
- Values are compared using Python equality semantics.
- None is treated as a regular value.
- Multiple documents with a missing constrained field are allowed.
- Documents with unhashable field values must be supported.
- Existing documents are checked when add_unique is called.

## Lifecycle

Constraints belong to the Table instance.

They are not persisted in storage metadata.

After reopening the database, the application
must register constraints again using add_unique().

## Atomicity

A rejected write operation must:

- Not persist any changes.
- Preserve the previous table state.
- Preserve existing unique constraints.

## Error Handling

Raise ValueError when:

- A new document violates a unique constraint.
- An update introduces duplicate values.
- Existing documents prevent constraint registration.
- The field argument is invalid.

Error messages should identify the constrained field.

## Documentation

Document:

- add_unique() public API.
- Constraint behavior.
- Supported write operations.
- Constraint lifecycle.
- Exception behavior.

## Acceptance Criteria

AC-01: Unique values can be registered.

AC-02: Duplicate insertions are rejected.

AC-03: Batch insertions are atomic.

AC-04: Updates cannot introduce duplicates.

AC-05: update_multiple respects constraints.

AC-06: Upsert respects constraints.

AC-07: Existing duplicates prevent registration.

AC-08: Missing fields are ignored.

AC-09: Unhashable values are supported.

AC-10: Failed operations do not persist changes.

AC-11: Existing TinyDB tests continue to pass.

AC-12: Documentation describes the new API.

## Constraints

- No external dependencies.
- No unrelated refactoring.
- Preserve existing public APIs.
- Follow the existing project coding style.

## Deliberately Underspecified Requirement

The exact internal implementation of uniqueness validation
is left to the implementing agent.

The agent must inspect the existing architecture,
evaluate possible approaches and choose the simplest
solution that satisfies all acceptance criteria.

Document the implementation decision.