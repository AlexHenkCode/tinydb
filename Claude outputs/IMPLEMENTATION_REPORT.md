# Implementation Report: Unique Field Constraints

Phase 6 of PROTOCOL.md. Feature: `Table.add_unique(field)` as specified in
SPEC.md, following IMPLEMENTATION_PLAN.md.

## Implemented functionality

- `Table.add_unique(field: str) -> None` registers a unique constraint for a
  top-level field of the table.
  - `field` must be a non-empty `str`. Otherwise it raises `ValueError`.
  - Registration is idempotent.
  - Existing documents are checked first. Duplicates raise `ValueError`, and
    the constraint is not activated.
  - Multiple constraints per table are supported. Each table has its own
    constraints.
- All writes are validated against the **resulting** table state: `insert`,
  `insert_multiple`, every `update` form, `update_multiple`, `upsert` (update
  and insert path), `remove` and `truncate`.
- A rejected write raises `ValueError` naming the field and value
  (`Unique constraint violated: duplicate value 'x' for field 'email'`). It
  doesn't write anything and doesn't change the stored documents, even with
  `MemoryStorage` or `CachingMiddleware`, which hand out the stored documents
  themselves.
- Semantics: Python equality (`1 == 1.0`), `None` is a regular value,
  missing fields are ignored, and unhashable values (lists, dicts) are
  supported.
- Lifecycle: constraints live on the `Table` instance. They are not
  persisted and must be registered again after reopening.

## Architecture decisions

- **One validation point:** `Table._update_table`, which every table write
  goes through. After `updater(table)` runs, `_check_unique` checks the new
  table and raises before `storage.write()`. There is no per-operation
  validation logic.
- **Copy only when needed:** if at least one constraint is registered,
  `_update_table` deep-copies the documents before running the updater.
  Updates mutate documents in place, so without the copy a rejected update
  would already have changed the data in memory-based storages. Tables
  without constraints behave exactly as before: no copy and no check.
- **Duplicate detection:** a `set` for hashable values and a list with `==`
  comparison as a fallback for unhashable values.
- **Change from the plan:** the plan proposed resetting `_next_id` after a
  rejected write. I left that out, because the reset would make TinyDB
  compute the next ID again from storage. That could reuse the ID of a
  document removed earlier in the same session, which TinyDB currently
  avoids. As a result, a rejected `insert`/`insert_multiple` may skip document
  IDs, but no ID is ever reused and no data is affected.

## Modified files

| File | Change |
|---|---|
| `tinydb/table.py` | `import copy`, `Any`; `_unique_fields`; `add_unique()`; `_check_unique()`; deep copy and check in `_update_table()` (additions only, +92 lines) |
| `docs/usage.rst` | new subsection "Unique Constraints" under "Tables" (additions only, +48 lines) |

Not modified: `docs/api.rst` (it already documents all `Table` members via
autodoc, so `add_unique` appears automatically). Line endings (CRLF) are
preserved.

Created earlier: `tests/test_unique_constraints.py`, `ANALYSIS.md`,
`IMPLEMENTATION_PLAN.md`, and this report.

## Tests

`tests/test_unique_constraints.py`: 64 test functions, each run on
`MemoryStorage`, `CachingMiddleware(MemoryStorage)` and `JSONStorage`, so 192
test runs. See IMPLEMENTATION_PLAN.md for the mapping from AC to tests.

## Commands executed and actual results

Run in a separate workspace (Linux, Python 3.13.18) on a copy of the
repository files. **Not run on the target Windows machine.**

| Command | Result |
|---|---|
| `python -m pytest` (baseline, before the change) | 228 passed |
| `python -m pytest tests/test_unique_constraints.py` (before the change) | 192 failed/errors, all `AttributeError: 'Table' object has no attribute 'add_unique'` |
| `python -m pytest tests/test_unique_constraints.py` | 192 passed |
| `python -m pytest` (full suite) | 420 passed; coverage `tinydb/table.py` 98%, total 94% |
| `python -m mypy tinydb` | Success: no issues found in 10 source files (same as baseline) |
| `python -m pycodestyle tinydb/table.py` | no new warnings (6 before, 6 after, all in existing code) |
| `sphinx-build -b html` (usage.rst + api.rst with autodoc) | no warnings from the new section or docstring; one existing warning in the `upsert` docstring |

Additional check: the test suite was run against a variant without the deep
copy. 24 atomicity tests failed on the memory and caching storages, which
confirms the tests detect partial in-place modifications.

## Known limitations / unresolved points

- Constraints only apply to writes through the same `Table` instance. Other
  `TinyDB` objects or external processes writing the same file are not
  checked (as SPEC.md specifies, documented in usage.rst).
- Each write with active constraints costs O(n) plus a deep copy of the table.
  That is acceptable given TinyDB's whole-table read and write model.
  Unhashable values are compared pairwise (O(k²)).
- Dotted field names (`'a.b'`) are treated as literal top-level keys. Nested
  paths are not supported.
- `True == 1` and NaN follow Python semantics (`True`/`1` are duplicates, and
  NaN never matches).
- A rejected insert may leave a gap in document IDs (see above).
- Subclasses overriding `_update_table` bypass validation.
- `docs/changelog.rst` was not updated, to keep the change minimal and
  because there is no "unreleased" section yet. Add an entry when you release.
- Before merging, run the suite on your machine (`uv run pytest`).
