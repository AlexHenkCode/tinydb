# Implementation Plan: Unique Field Constraints

Phase 2 of PROTOCOL.md. See docs/ANALYSIS.md for the background.

## Proposed architecture

Validate the **resulting table state** in `Table._update_table`, after the
updater has run and before anything is written.

1. `Table.__init__`: add `self._unique_fields: list[str] = []`. This state
   belongs to the instance and is not persisted.
2. `Table.add_unique(field: str) -> None` (public, with a docstring):
   - Raise `ValueError` if `field` is not a non-empty `str`.
   - If `field` is already registered, return (idempotent).
   - Check the current documents with `_check_unique(self._read_table(),
     [field])`. A duplicate raises `ValueError`, and the field is **not**
     added.
   - Append `field` to `_unique_fields`.
3. `Table._check_unique(table, fields)` (private): for each field, collect
   the values of the documents that contain the field.
   - Hashable values go into a `set` (O(1) lookup, Python `==` and hash
     semantics).
   - Unhashable values (`TypeError` on hashing) go into a list and are
     compared with `in` (Python `==`).
   - Missing fields are skipped. `None` is a regular value.
   - On the first duplicate, raise
     `ValueError("Duplicate value for unique field 'email': ...")`.
4. `Table._update_table`:
   - If `_unique_fields` is non-empty, `copy.deepcopy` the document dicts
     before calling the updater. The updater can then never mutate the
     shared documents of `MemoryStorage` or `CachingMiddleware`, even
     through callables that change nested values.
   - After `updater(table)`, call `self._check_unique(table,
     self._unique_fields)`.
   - If the updater or the check raises, reset `self._next_id = None` (so
     the next ID is computed again from storage) and re-raise. Nothing has
     been written yet.

### Why this approach

- **One validation point** covers insert, insert_multiple, all update
  forms, update_multiple, upsert (made of update + insert), remove and
  truncate. There is no duplicated validation logic (CONSTITUTION §2).
- **The resulting state is validated**, as FR-04 requires. Temporary
  duplicates while documents are processed in order (such as swaps) are
  allowed.
- **Batches are validated as a whole**, because the check sees the whole
  table after the batch.
- **No behavior change without constraints**: the deep copy and the check
  only run when at least one constraint is registered.

### Alternatives considered

- *Check each operation before the write* (compute the new documents and
  compare them): duplicates the update semantics of `update` and
  `update_multiple` and is error-prone. Rejected.
- *Keep an index of values per field*: faster, but it would have to stay in
  sync with external writes, other `Table` instances and failed writes.
  That's too complex for TinyDB's whole-table read and write model.
  Rejected.

## Files to modify

| File | Change |
|---|---|
| `tinydb/table.py` | `import copy`, `_unique_fields`, `add_unique`, `_check_unique`, integration into `_update_table` |
| `tests/test_unique_constraints.py` | new test module (already written) |
| `docs/usage.rst` | new section "Unique constraints" |
| `docs/changelog.rst` | entry under unreleased |
| `docs/api.rst` | nothing needed if `Table` is documented with `:members:` (to be checked) |

## Validation strategy

- Cost: O(n) per write over the whole table, plus a deep copy, only when
  constraints are active. This matches TinyDB's existing O(n) read and
  write per operation.
- Unhashable values: in the worst case O(k²) for k unhashable values per
  field.

## Test scenarios → acceptance criteria

All tests are in `tests/test_unique_constraints.py`. They run on
`MemoryStorage`, `CachingMiddleware(MemoryStorage)` and `JSONStorage`. Each
rejection checks the `ValueError`, that the message names the field, and
that the table is unchanged.

| AC | Tests |
|---|---|
| AC-01 register | `test_add_unique_on_empty_table`, `..._with_unique_existing_documents`, `..._is_idempotent`, `test_multiple_constraints_on_one_table`, `..._rejects_invalid_field`, `test_constraints_are_scoped_to_table`, `test_add_unique_on_default_table` |
| AC-02 insert | `test_insert_*` |
| AC-03 batch atomic | `test_insert_multiple_*` (existing, within the batch, generator, Document IDs) |
| AC-04 update | `test_update_*` (all 5 forms in SPEC.md + callable-all, resulting state, field removal, nested in-place mutation) |
| AC-05 update_multiple | `test_update_multiple_*` |
| AC-06 upsert | `test_upsert_*` (update path, insert path, Document doc_id) |
| AC-07 existing duplicates | `test_add_unique_rejects_existing_duplicates`, `test_failed_registration_keeps_other_constraints`, `test_none_/unhashable_duplicates_prevent_registration` |
| AC-08 missing fields | `test_missing_fields_are_ignored`, `test_none_is_a_regular_value` |
| AC-09 unhashable | `test_unhashable_*` |
| AC-10 no persistence on failure | `assert_rejected` in all tests + `test_failed_operation_does_not_change_file` |
| AC-11 existing tests | full suite run |
| AC-12 docs | usage.rst / changelog.rst review |
| FR-07 remove | `test_remove_*`, `test_truncate_keeps_constraint` |
| Lifecycle | `test_constraints_are_not_persisted` |

## Compatibility risks

- Subclasses that override `_update_table` skip validation. This is
  acceptable because it's private API, but should be documented.
- `copy.deepcopy` fails for custom storages that return non-copyable
  objects. Only relevant when constraints are active.
- With constraints active, callables passed to `update` receive a copy.
  Keeping a reference to the document after the call no longer reaches the
  stored data. This only affects code that relies on undocumented
  behavior.
- A rejected write resets `_next_id`. No ID is reused, because it is
  computed again from `max(id) + 1`.
- Writes through another `Table` instance or `TinyDB` object on the same
  file are not checked (constraints belong to the instance). This should be
  documented as a limitation.
