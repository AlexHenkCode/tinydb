"""
Tests for unique field constraints (``Table.add_unique``).

The scenarios map to the requirements in SPEC.md:

- FR-01 / AC-01, AC-07: registration
- FR-02 / AC-02: insert
- FR-03 / AC-03: insert_multiple
- FR-04 / AC-04: update
- FR-05 / AC-05: update_multiple
- FR-06 / AC-06: upsert
- FR-07: remove / truncate
- AC-08, AC-09: missing fields, ``None`` and unhashable values
- AC-10: failed operations do not persist changes
- Lifecycle: constraints are not persisted

Every rejected operation is checked against the table state before the
operation, so atomicity is verified for all storages used by the fixture.
"""
import copy

import pytest

from tinydb import TinyDB, where
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage, MemoryStorage
from tinydb.table import Document


ALICE = 'alice@example.com'
BOB = 'bob@example.com'


@pytest.fixture(params=['memory', 'caching', 'json'])
def db(request, tmp_path):
    if request.param == 'json':
        db_ = TinyDB(tmp_path / 'test.db', storage=JSONStorage)
    elif request.param == 'caching':
        db_ = TinyDB(storage=CachingMiddleware(MemoryStorage))
    else:
        db_ = TinyDB(storage=MemoryStorage)

    yield db_

    db_.close()


@pytest.fixture
def users(db):
    """
    A ``users`` table with a unique ``email`` constraint.

    Document IDs: 1 = alice, 2 = bob, 3 = carol (no email field).
    """
    table = db.table('users')
    table.insert_multiple([
        {'name': 'alice', 'email': ALICE},
        {'name': 'bob', 'email': BOB},
        {'name': 'carol'},
    ])
    table.add_unique('email')

    return table


def snapshot(table):
    """
    Return a deep copy of the table contents including document IDs.
    """
    return {doc.doc_id: copy.deepcopy(dict(doc)) for doc in table}


def assert_rejected(table, field, operation):
    """
    Assert that ``operation`` raises a ``ValueError`` naming ``field`` and
    that the table contents are unchanged afterwards.
    """
    before = snapshot(table)

    with pytest.raises(ValueError, match=field):
        operation()

    assert snapshot(table) == before


def set_email(value):
    def transform(doc):
        doc['email'] = value

    return transform


# ---------------------------------------------------------------------------
# FR-01: Registration
# ---------------------------------------------------------------------------

def test_add_unique_on_empty_table(db):
    table = db.table('users')
    table.add_unique('email')

    table.insert({'email': ALICE})
    assert_rejected(table, 'email', lambda: table.insert({'email': ALICE}))
    assert len(table) == 1


def test_add_unique_with_unique_existing_documents(db):
    table = db.table('users')
    table.insert_multiple([{'email': ALICE}, {'email': BOB}])
    before = snapshot(table)

    table.add_unique('email')

    assert snapshot(table) == before
    assert_rejected(table, 'email', lambda: table.insert({'email': BOB}))


def test_add_unique_rejects_existing_duplicates(db):
    table = db.table('users')
    table.insert_multiple([{'email': ALICE}, {'email': ALICE}])
    before = snapshot(table)

    with pytest.raises(ValueError, match='email'):
        table.add_unique('email')

    # Registration must not touch the data ...
    assert snapshot(table) == before

    # ... and the failed constraint must not be active
    table.insert({'email': ALICE})
    assert table.count(where('email') == ALICE) == 3


def test_failed_registration_keeps_other_constraints(db):
    table = db.table('users')
    table.insert_multiple([
        {'email': ALICE, 'name': 'same'},
        {'email': BOB, 'name': 'same'},
    ])
    table.add_unique('email')

    with pytest.raises(ValueError, match='name'):
        table.add_unique('name')

    # The ``email`` constraint is still active
    assert_rejected(table, 'email', lambda: table.insert({'email': ALICE}))

    # The ``name`` constraint was not activated
    table.insert({'email': 'new@example.com', 'name': 'same'})
    assert table.count(where('name') == 'same') == 3


def test_add_unique_is_idempotent(users):
    users.add_unique('email')
    users.add_unique('email')

    assert_rejected(users, 'email', lambda: users.insert({'email': ALICE}))

    # Registering the constraint multiple times must not change its
    # behaviour once the value has been freed again
    users.remove(where('email') == ALICE)
    users.insert({'email': ALICE})
    assert users.count(where('email') == ALICE) == 1


def test_multiple_constraints_on_one_table(db):
    table = db.table('users')
    table.add_unique('email')
    table.add_unique('username')

    table.insert({'email': ALICE, 'username': 'alice'})

    assert_rejected(table, 'email', lambda: table.insert(
        {'email': ALICE, 'username': 'other'}
    ))
    assert_rejected(table, 'username', lambda: table.insert(
        {'email': 'other@example.com', 'username': 'alice'}
    ))

    table.insert({'email': BOB, 'username': 'bob'})
    assert len(table) == 2


@pytest.mark.parametrize('field', ['', None, 1, ['email'], b'email'])
def test_add_unique_rejects_invalid_field(db, field):
    table = db.table('users')
    table.insert_multiple([{'email': ALICE}, {'email': ALICE}])
    before = snapshot(table)

    with pytest.raises(ValueError):
        table.add_unique(field)

    assert snapshot(table) == before

    # No constraint has been activated by the failed call
    table.insert({'email': ALICE})
    assert len(table) == 3


def test_constraints_are_scoped_to_table(db):
    users = db.table('users')
    admins = db.table('admins')
    users.add_unique('email')

    users.insert({'email': ALICE})

    # The same value is allowed in another table ...
    admins.insert({'email': ALICE})
    # ... and the other table has no constraint at all
    admins.insert({'email': ALICE})
    assert len(admins) == 2

    # Registering the same field on the other table only checks that table
    admins.truncate()
    admins.add_unique('email')
    admins.insert({'email': ALICE})
    assert_rejected(admins, 'email', lambda: admins.insert({'email': ALICE}))
    assert_rejected(users, 'email', lambda: users.insert({'email': ALICE}))


def test_add_unique_on_default_table(db):
    db.insert({'email': ALICE})
    db.add_unique('email')

    assert_rejected(db, 'email', lambda: db.insert({'email': ALICE}))
    assert len(db) == 1


# ---------------------------------------------------------------------------
# FR-02: Insert
# ---------------------------------------------------------------------------

def test_insert_unique_value(users):
    doc_id = users.insert({'name': 'dave', 'email': 'dave@example.com'})

    assert users.get(doc_id=doc_id) == {
        'name': 'dave', 'email': 'dave@example.com'
    }


def test_insert_duplicate_is_rejected(users):
    assert_rejected(users, 'email', lambda: users.insert(
        {'name': 'mallory', 'email': ALICE}
    ))


def test_insert_document_with_doc_id_duplicate_is_rejected(users):
    assert_rejected(users, 'email', lambda: users.insert(
        Document({'email': BOB}, doc_id=10)
    ))
    assert not users.contains(doc_id=10)


def test_insert_after_rejection_still_works(users):
    with pytest.raises(ValueError):
        users.insert({'email': ALICE})

    # The constraint is still active ...
    assert_rejected(users, 'email', lambda: users.insert({'email': ALICE}))

    # ... and valid inserts still succeed with unique IDs
    doc_id = users.insert({'email': 'dave@example.com'})
    assert users.get(doc_id=doc_id) == {'email': 'dave@example.com'}
    assert len({doc.doc_id for doc in users}) == len(users) == 4


# ---------------------------------------------------------------------------
# FR-03: Insert multiple
# ---------------------------------------------------------------------------

def test_insert_multiple_unique_values(users):
    doc_ids = users.insert_multiple([
        {'email': 'dave@example.com'},
        {'email': 'erin@example.com'},
    ])

    assert len(doc_ids) == 2
    assert len(users) == 5


def test_insert_multiple_conflict_with_existing_is_atomic(users):
    assert_rejected(users, 'email', lambda: users.insert_multiple([
        {'email': 'dave@example.com'},
        {'email': ALICE},
        {'email': 'erin@example.com'},
    ]))


def test_insert_multiple_conflict_within_batch_is_atomic(users):
    assert_rejected(users, 'email', lambda: users.insert_multiple([
        {'email': 'dave@example.com'},
        {'email': 'erin@example.com'},
        {'email': 'dave@example.com'},
    ]))


def test_insert_multiple_conflict_from_generator_is_atomic(users):
    emails = ['dave@example.com', 'erin@example.com', 'dave@example.com']

    assert_rejected(users, 'email', lambda: users.insert_multiple(
        {'email': email} for email in emails
    ))


def test_insert_multiple_with_document_ids_conflict_is_atomic(users):
    assert_rejected(users, 'email', lambda: users.insert_multiple([
        Document({'email': 'dave@example.com'}, doc_id=10),
        Document({'email': 'dave@example.com'}, doc_id=11),
    ]))


def test_insert_multiple_after_rejection_still_works(users):
    with pytest.raises(ValueError):
        users.insert_multiple([{'email': 'x@example.com'}, {'email': BOB}])

    doc_ids = users.insert_multiple([
        {'email': 'x@example.com'},
        {'email': 'y@example.com'},
    ])

    assert len(doc_ids) == 2
    assert len({doc.doc_id for doc in users}) == len(users) == 5


# ---------------------------------------------------------------------------
# FR-04: Update
# ---------------------------------------------------------------------------

DUPLICATING_UPDATES = {
    'mapping-cond': lambda t: t.update(
        {'email': ALICE}, where('name') == 'bob'
    ),
    'mapping-doc_ids': lambda t: t.update(
        {'email': ALICE}, doc_ids=[2]
    ),
    'callable-cond': lambda t: t.update(
        set_email(ALICE), where('name') == 'bob'
    ),
    'callable-doc_ids': lambda t: t.update(
        set_email(ALICE), doc_ids=[2]
    ),
    'mapping-all': lambda t: t.update(
        {'email': 'same@example.com'}
    ),
    'callable-all': lambda t: t.update(
        set_email('same@example.com')
    ),
    'missing-field-gains-duplicate': lambda t: t.update(
        {'email': BOB}, where('name') == 'carol'
    ),
}


@pytest.mark.parametrize(
    'operation', DUPLICATING_UPDATES.values(), ids=DUPLICATING_UPDATES.keys()
)
def test_update_introducing_duplicate_is_rejected(users, operation):
    assert_rejected(users, 'email', lambda: operation(users))

    # The constraint is still active after the rejected update
    assert_rejected(users, 'email', lambda: users.insert({'email': ALICE}))


VALID_UPDATES = {
    'mapping-cond': lambda t: t.update(
        {'email': 'new@example.com'}, where('name') == 'bob'
    ),
    'mapping-doc_ids': lambda t: t.update(
        {'email': 'new@example.com'}, doc_ids=[2]
    ),
    'callable-cond': lambda t: t.update(
        set_email('new@example.com'), where('name') == 'bob'
    ),
    'callable-doc_ids': lambda t: t.update(
        set_email('new@example.com'), doc_ids=[2]
    ),
}


@pytest.mark.parametrize(
    'operation', VALID_UPDATES.values(), ids=VALID_UPDATES.keys()
)
def test_update_to_unique_value(users, operation):
    assert operation(users) == [2]
    assert users.get(doc_id=2)['email'] == 'new@example.com'

    # The old value is free again
    users.insert({'email': BOB})
    assert users.count(where('email') == BOB) == 1


def test_update_keeping_own_value(users):
    assert users.update(
        {'email': ALICE, 'name': 'alice2'}, where('name') == 'alice'
    ) == [1]
    assert users.get(doc_id=1) == {'name': 'alice2', 'email': ALICE}


def test_update_without_filter_on_single_document(db):
    table = db.table('users')
    table.add_unique('email')
    table.insert({'email': ALICE})

    assert table.update({'email': BOB}) == [1]
    assert table.all() == [{'email': BOB}]


def test_update_validates_resulting_state(users):
    # Swapping two values creates a temporary duplicate while documents
    # are updated one after another. Only the final state counts.
    swap = {ALICE: BOB, BOB: ALICE}

    def swap_email(doc):
        if 'email' in doc:
            doc['email'] = swap[doc['email']]

    users.update(swap_email)

    assert users.get(doc_id=1)['email'] == BOB
    assert users.get(doc_id=2)['email'] == ALICE


def test_update_removing_field_from_multiple_documents(users):
    users.update(lambda doc: doc.pop('email', None))

    assert users.count(where('email').exists()) == 0

    users.insert({'email': ALICE})
    assert_rejected(users, 'email', lambda: users.insert({'email': ALICE}))


def test_update_with_nested_in_place_mutation_is_atomic(db):
    table = db.table('things')
    table.insert_multiple([{'tags': ['a']}, {'tags': ['b']}])
    table.add_unique('tags')

    def mutate_in_place(doc):
        doc['tags'].clear()
        doc['tags'].append('a')

    assert_rejected(table, 'tags', lambda: table.update(
        mutate_in_place, doc_ids=[2]
    ))
    assert table.get(doc_id=2) == {'tags': ['b']}


# ---------------------------------------------------------------------------
# FR-05: Update multiple
# ---------------------------------------------------------------------------

def test_update_multiple_introducing_duplicate_is_rejected(users):
    assert_rejected(users, 'email', lambda: users.update_multiple([
        ({'email': 'same@example.com'}, where('name') == 'alice'),
        ({'email': 'same@example.com'}, where('name') == 'bob'),
    ]))


def test_update_multiple_duplicate_with_unchanged_document(users):
    assert_rejected(users, 'email', lambda: users.update_multiple([
        ({'name': 'robert'}, where('name') == 'bob'),
        (set_email(BOB), where('name') == 'carol'),
    ]))


def test_update_multiple_unique_values(users):
    users.update_multiple([
        ({'email': 'a2@example.com'}, where('name') == 'alice'),
        (set_email('b2@example.com'), where('name') == 'bob'),
    ])

    assert users.get(doc_id=1)['email'] == 'a2@example.com'
    assert users.get(doc_id=2)['email'] == 'b2@example.com'


def test_update_multiple_validates_resulting_state(users):
    # alice -> bob's address while bob moves to a new address. Documents
    # are processed in order, so alice temporarily duplicates bob.
    users.update_multiple([
        ({'email': 'new@example.com'}, where('email') == BOB),
        ({'email': BOB}, where('email') == ALICE),
    ])

    assert users.get(doc_id=1)['email'] == BOB
    assert users.get(doc_id=2)['email'] == 'new@example.com'


# ---------------------------------------------------------------------------
# FR-06: Upsert
# ---------------------------------------------------------------------------

def test_upsert_update_introducing_duplicate_is_rejected(users):
    assert_rejected(users, 'email', lambda: users.upsert(
        {'email': ALICE}, where('name') == 'bob'
    ))


def test_upsert_insert_introducing_duplicate_is_rejected(users):
    assert_rejected(users, 'email', lambda: users.upsert(
        {'name': 'dave', 'email': ALICE}, where('name') == 'dave'
    ))


def test_upsert_document_update_introducing_duplicate_is_rejected(users):
    assert_rejected(users, 'email', lambda: users.upsert(
        Document({'email': ALICE}, doc_id=2)
    ))


def test_upsert_document_insert_introducing_duplicate_is_rejected(users):
    assert_rejected(users, 'email', lambda: users.upsert(
        Document({'email': ALICE}, doc_id=10)
    ))
    assert not users.contains(doc_id=10)


def test_upsert_update_keeping_own_value(users):
    assert users.upsert(
        {'name': 'alice2', 'email': ALICE}, where('email') == ALICE
    ) == [1]
    assert users.get(doc_id=1) == {'name': 'alice2', 'email': ALICE}


def test_upsert_insert_unique_value(users):
    doc_ids = users.upsert(
        {'name': 'dave', 'email': 'dave@example.com'}, where('name') == 'dave'
    )

    assert len(doc_ids) == 1
    assert users.get(doc_id=doc_ids[0])['email'] == 'dave@example.com'


# ---------------------------------------------------------------------------
# FR-07: Remove
# ---------------------------------------------------------------------------

def test_remove_by_query_frees_value(users):
    assert users.remove(where('email') == ALICE) == [1]

    users.insert({'email': ALICE})
    assert_rejected(users, 'email', lambda: users.insert({'email': ALICE}))


def test_remove_by_doc_ids_frees_value(users):
    assert users.remove(doc_ids=[2]) == [2]

    users.insert({'email': BOB})
    assert_rejected(users, 'email', lambda: users.insert({'email': BOB}))


def test_truncate_keeps_constraint(users):
    users.truncate()
    assert len(users) == 0

    users.insert({'email': ALICE})
    assert_rejected(users, 'email', lambda: users.insert({'email': ALICE}))


# ---------------------------------------------------------------------------
# Constraint semantics: missing fields, None, equality, unhashable values
# ---------------------------------------------------------------------------

def test_missing_fields_are_ignored(db):
    table = db.table('users')
    table.insert_multiple([{'name': 'a'}, {'name': 'b'}])

    # Registration ignores documents without the field
    table.add_unique('email')

    table.insert({'name': 'c'})
    table.insert_multiple([{'name': 'd'}, {'name': 'e'}])
    table.update({'name': 'x'}, where('name') == 'a')

    assert len(table) == 5


def test_none_is_a_regular_value(db):
    table = db.table('users')
    table.add_unique('email')

    table.insert({'email': None})
    # A missing field does not conflict with ``None``
    table.insert({'name': 'no email'})

    assert_rejected(table, 'email', lambda: table.insert({'email': None}))


def test_none_duplicates_prevent_registration(db):
    table = db.table('users')
    table.insert_multiple([{'email': None}, {'email': None}])

    with pytest.raises(ValueError, match='email'):
        table.add_unique('email')


def test_values_use_python_equality(db):
    table = db.table('things')
    table.add_unique('value')

    table.insert({'value': 1})
    # Different type, not equal: allowed
    table.insert({'value': '1'})

    # 1 == 1.0 in Python: rejected
    assert_rejected(table, 'value', lambda: table.insert({'value': 1.0}))


@pytest.mark.parametrize('value', [
    [1, 2],
    {'street': 'Main St', 'number': 1},
    [{'nested': [1, 2]}],
], ids=['list', 'dict', 'nested'])
def test_unhashable_values_are_supported(db, value):
    table = db.table('things')
    table.add_unique('value')

    table.insert({'value': copy.deepcopy(value)})
    assert_rejected(table, 'value', lambda: table.insert(
        {'value': copy.deepcopy(value)}
    ))

    table.insert({'value': 'hashable'})
    table.insert({'value': [value]})
    assert len(table) == 3


def test_unhashable_values_order_matters(db):
    table = db.table('things')
    table.add_unique('value')

    table.insert({'value': [1, 2]})
    table.insert({'value': [2, 1]})

    assert len(table) == 2


def test_unhashable_duplicates_prevent_registration(db):
    table = db.table('things')
    table.insert_multiple([{'value': [1, 2]}, {'value': [1, 2]}])

    with pytest.raises(ValueError, match='value'):
        table.add_unique('value')


def test_unhashable_duplicates_in_batch_are_rejected(db):
    table = db.table('things')
    table.add_unique('value')

    assert_rejected(table, 'value', lambda: table.insert_multiple([
        {'value': {'a': 1}},
        {'value': {'a': 1}},
    ]))


# ---------------------------------------------------------------------------
# AC-10: Failed operations do not persist changes
# ---------------------------------------------------------------------------

FAILING_OPERATIONS = {
    'insert': lambda t: t.insert({'email': ALICE}),
    'insert_multiple': lambda t: t.insert_multiple(
        [{'email': 'x@example.com'}, {'email': ALICE}]
    ),
    'update': lambda t: t.update({'email': ALICE}, where('name') == 'bob'),
    'update_multiple': lambda t: t.update_multiple(
        [({'email': ALICE}, where('name') == 'bob')]
    ),
    'upsert': lambda t: t.upsert({'email': ALICE}, where('name') == 'bob'),
}


@pytest.mark.parametrize(
    'operation', FAILING_OPERATIONS.values(), ids=FAILING_OPERATIONS.keys()
)
def test_failed_operation_does_not_change_file(tmp_path, operation):
    path = tmp_path / 'db.json'

    with TinyDB(path) as db:
        table = db.table('users')
        table.insert_multiple([
            {'name': 'alice', 'email': ALICE},
            {'name': 'bob', 'email': BOB},
        ])
        table.add_unique('email')

        content = path.read_text()

        with pytest.raises(ValueError, match='email'):
            operation(table)

        assert path.read_text() == content


# ---------------------------------------------------------------------------
# Lifecycle: constraints are not persisted
# ---------------------------------------------------------------------------

def test_constraints_are_not_persisted(tmp_path):
    path = tmp_path / 'db.json'

    with TinyDB(path) as db:
        table = db.table('users')
        table.add_unique('email')
        table.insert({'email': ALICE})

    # No constraint metadata is stored
    with TinyDB(path) as db:
        assert db.storage.read() == {'users': {'1': {'email': ALICE}}}

    # After reopening, the constraint must be registered again
    with TinyDB(path) as db:
        table = db.table('users')
        table.insert({'email': ALICE})
        assert len(table) == 2

        with pytest.raises(ValueError, match='email'):
            table.add_unique('email')