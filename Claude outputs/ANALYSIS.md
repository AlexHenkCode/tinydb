# Analysis: Unique Field Constraints

Phase 1 of PROTOCOL.md. No implementation files were modified.

## Project setup

- Python `>=3.10`, build backend hatchling, dev tooling via `uv` (uv.lock).
- Tests: pytest, configured in `pytest.ini` (`--cov tinydb`).
- Type checking: mypy with `tinydb/mypy_plugin.py` (`pytest-mypy` in dev deps).
- Style: `pycodestyle` / `pytest-pycodestyle` in dev deps (not enabled in
  `addopts`).
- Docs: Sphinx (`docs/usage.rst`, `docs/api.rst`, `docs/changelog.rst`).
- Baseline: the existing suite has 228 tests and all pass (Python 3.13, run
  in a separate workspace, not on the target machine).

## Exception conventions

`Table` raises `ValueError` for invalid input and data conflicts (for
example `'Document is not a Mapping'` and `'Document with ID ... already
exists'`). It raises `RuntimeError` for invalid argument combinations. The
new feature uses `ValueError`, as SPEC.md requires.

## Write operations in `tinydb/table.py`

| Operation | Path to storage | Notes |
|---|---|---|
| `__init__(persist_empty=True)` | `_update_table` (clear) | only for new, empty tables |
| `insert` | `_update_table` | calls `_get_next_id()` *before* the updater |
| `insert_multiple` | `_update_table` | consumes the iterable inside the updater; advances `_next_id` |
| `update` (mapping/callable × cond/doc_ids/all) | `_update_table` | mutates `table[doc_id]` **in place** |
| `update_multiple` | `_update_table` | in place; applies updates per document, in sequence |
| `upsert` | `update()` then possibly `insert()` | two separate writes |
| `remove` (cond / doc_ids) | `_update_table` | |
| `truncate` | `_update_table` | resets `_next_id` |

`TinyDB.drop_table(s)` write to storage directly. They delete tables and
drop the cached `Table` instances, so constraints don't apply to them.
`TinyDB.__getattr__` forwards unknown attributes to the default table, so
`db.add_unique(...)` works automatically.

## Common write mechanism

All table writes go through `Table._update_table(updater)`:

1. `tables = storage.read()`
2. Build `table = {doc_id_class(k): doc for k, doc in raw_table.items()}`.
   This is a new outer dict, but the **document dicts are shared** with what
   `read()` returned.
3. `updater(table)`
4. `tables[self.name] = {...}` and then `storage.write(tables)`
5. `clear_cache()`

This is the one place where the final state of the table is known before it
is written. It's the natural place to validate uniqueness.

## Current atomicity behavior

- `JSONStorage.read()` returns freshly parsed data, so an exception in the
  updater leaves the file unchanged.
- `MemoryStorage.read()` returns `self.memory` itself, and
  `CachingMiddleware.read()` returns its cache. With these storages,
  `update`/`update_multiple` mutate the stored documents **before**
  `write()`. If the write is rejected after the updater runs, the data has
  already changed. **The feature must not validate on the shared
  documents.**
- `insert` and `insert_multiple` advance `self._next_id` even when the write
  fails. That leaves gaps in the document IDs but doesn't corrupt data.
- `upsert` is two writes (`update` and then `insert`). Each write is
  validated on its own. Only one of them changes data, so a rejected upsert
  leaves no partial state.

## Existing test organization

`tests/conftest.py` provides a `db` fixture parametrized over memory and
JSON storage. Tests are plain pytest functions grouped by module
(`test_tables.py`, `test_tinydb.py`, …). The new tests go into a new module,
`tests/test_unique_constraints.py`.

## Open points / assumptions

- **Dotted field names** (such as `'address.city'`) are not specified. They
  are treated as literal top-level keys and are not tested.
- **Python equality** means `1 == 1.0 == True` count as duplicates. This
  follows SPEC.md literally.
- **NaN**: `float('nan') != float('nan')`, so NaN values never conflict.
  This edge case is not tested.
- **`add_unique` on an already registered field** returns without checking
  the data again. Data can't violate an active constraint, so this is safe.
