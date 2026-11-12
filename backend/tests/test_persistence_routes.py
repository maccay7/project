"""Persistence failure-path tests that use isolated fake database connections."""

from contextlib import contextmanager

import pytest
from app import app
from routes import dataset, reports, sessions, version_history
import migrate
import io


class FakeCursor:
    def __init__(self, row=None, rows=None, failure=None):
        self.row = row
        self.rows = rows or []
        self.failure = failure
        self.rowcount = 1
        self.lastrowid = 17
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        self._last_query = query
        if self.failure and self.failure(query, params):
            raise RuntimeError('simulated database failure')

    def fetchone(self):
        # information_schema existence probes must report the table as
        # present, otherwise routes take their no-table fallback path.
        if 'information_schema' in getattr(self, '_last_query', ''):
            return {'COUNT(*)': 1}
        return self.row

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self.test_cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.begun = False

    def cursor(self, *_args, **_kwargs):
        return self.test_cursor

    def begin(self):
        self.begun = True

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def install_db(monkeypatch, module, connection):
    @contextmanager
    def fake_db(*_args, **_kwargs):
        yield connection, connection.test_cursor

    monkeypatch.setattr(module, '_db', fake_db)


def test_load_dataset_preserves_saved_empty_values(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    install_db(monkeypatch, dataset, connection)
    monkeypatch.setattr(dataset, '_authenticated_user', lambda: (7, None))
    monkeypatch.setattr(dataset, '_owned_dataset', lambda *_args: {
        'id': 12,
        'name': 'Empty cleaned worksheet',
        'original_file_name': 'book.xlsx',
        'data': [],
        'headers': [],
        'metadata': {},
        'instrument_type': 'bonds',
        'file_path': 'missing.xlsx',
    })
    monkeypatch.setattr(
        dataset, 'intelligent_parse',
        lambda *_args: pytest.fail('Saved empty data must not fall back to workbook parsing')
    )

    response = app.test_client().post('/api/load-dataset', json={'dataset_id': 12})

    assert response.status_code == 200
    assert response.get_json()['data']['data'] == []
    assert response.get_json()['data']['headers'] == []


@pytest.mark.parametrize(
    ('method', 'path', 'payload'),
    [
        ('delete', '/api/dataset/99', None),
        ('post', '/api/delete-dataset', {'dataset_id': 99}),
    ],
)
def test_dataset_delete_returns_not_found_for_unowned_or_missing_record(
    monkeypatch, method, path, payload
):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    install_db(monkeypatch, dataset, connection)
    monkeypatch.setattr(dataset, '_authenticated_user', lambda: (7, None))
    monkeypatch.setattr(dataset, '_owned_dataset', lambda *_args: None)

    response = getattr(app.test_client(), method)(
        path, json=payload
    ) if payload is not None else getattr(app.test_client(), method)(path)

    assert response.status_code == 404
    assert response.get_json()['success'] is False
    assert not connection.committed


def test_dataset_metadata_transaction_rolls_back_if_upload_history_fails(monkeypatch):
    cursor = FakeCursor(failure=lambda query, _params: 'upload_history' in query)
    connection = FakeConnection(cursor)
    install_db(monkeypatch, dataset, connection)

    result = dataset.save_dataset_metadata(
        'stored.xlsx', 'original.xlsx', 'C:\\uploads\\stored.xlsx',
        123, 'bonds', 1, 4, 3, user_id=7, metadata={}
    )

    assert result is None
    assert connection.begun
    assert connection.rolled_back
    assert not connection.committed


def test_upload_removes_original_file_when_metadata_save_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(dataset, 'UPLOAD_FOLDER', str(tmp_path))
    monkeypatch.setattr(dataset, '_authenticated_user', lambda: (7, None))
    monkeypatch.setattr(dataset, '_parse_workbook_safely', lambda *_args: {
        'ok': True,
        'sheet_count': 1,
        'total_rows': 1,
        'total_columns': 1,
        'sheet_names': ['Sheet1'],
        'warnings': [],
    })
    monkeypatch.setattr(dataset, 'save_dataset_metadata', lambda *_args: None)

    response = app.test_client().post(
        '/api/dataset/upload',
        data={'file': (io.BytesIO(b'workbook'), 'source.xlsx')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 500
    assert response.get_json()['success'] is False
    assert list(tmp_path.iterdir()) == []


def test_report_metadata_failure_rolls_back(monkeypatch):
    cursor = FakeCursor(failure=lambda *_args: True)
    connection = FakeConnection(cursor)
    install_db(monkeypatch, reports, connection)

    result = reports.save_report(7, 'session-1', 'excel', {}, 'C:\\reports\\r.xlsx')

    assert result is None
    assert connection.begun
    assert connection.rolled_back
    assert not connection.committed


def test_report_file_is_removed_when_report_metadata_save_fails(monkeypatch, tmp_path):
    report_file = tmp_path / 'generated.xlsx'
    report_file.write_bytes(b'generated report')
    monkeypatch.setattr(
        reports, '_authenticated_session_owner', lambda _session_id: (7, None)
    )
    monkeypatch.setattr(
        reports, 'generate_report_excel', lambda *_args, **_kwargs: str(report_file)
    )
    monkeypatch.setattr(reports, 'save_report', lambda *_args: None)

    response = app.test_client().post('/api/report/generate', json={
        'session_id': 'session-1',
        'report_data': {},
    })

    assert response.status_code == 500
    assert response.get_json()['success'] is False
    assert not report_file.exists()


@pytest.mark.parametrize(
    ('stored_count', 'actual_count', 'expected_count'),
    [(1, 3, 3), (4, 0, 0)],
)
def test_session_get_uses_actual_version_count(
    monkeypatch, stored_count, actual_count, expected_count
):
    cursor = FakeCursor(row={
        'id': 'session-1',
        'name': 'Restored workflow',
        'status': 'in-progress',
        'versions': None,
        'instrument_workflows': None,
        'payload': None,
        'instrument_count': 0,
        'version_count': stored_count,
        'version_count_from_history': actual_count,
        'total_value': 0,
        'created_at': None,
        'updated_at': None,
    })
    connection = FakeConnection(cursor)
    install_db(monkeypatch, sessions, connection)
    monkeypatch.setattr(sessions, 'resolve_current_user', lambda: (7, None))

    response = app.test_client().post(
        '/api/sessions/get', json={'session_id': 'session-1'}
    )

    assert response.status_code == 200
    assert response.get_json()['data']['version_count'] == expected_count
    # The route first probes information_schema for the version_history
    # table, so the version-count query is not necessarily statements[0].
    version_stmt = next(
        (st for st in cursor.statements
         if 'WHERE vh.session_id = ui_sessions.session_id' in st[0]),
        None,
    )
    assert version_stmt is not None, 'version-count query not issued'
    assert version_stmt[1] == ('session-1', 7)


def test_version_history_database_failure_is_not_reported_as_empty_success(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    install_db(monkeypatch, version_history, connection)
    monkeypatch.setattr(version_history, 'resolve_current_user', lambda: (7, None))
    monkeypatch.setattr(version_history, 'session_is_owned', lambda *_args: True)
    monkeypatch.setattr(
        version_history, 'get_versions_by_session',
        lambda *_args: (_ for _ in ()).throw(RuntimeError('Database unavailable'))
    )

    response = app.test_client().get('/api/version/session/session-1')

    assert response.status_code == 500
    assert response.get_json() == {
        'success': False,
        'message': 'Database unavailable',
    }


def test_version_restore_persists_snapshot_transactionally(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    install_db(monkeypatch, version_history, connection)
    monkeypatch.setattr(version_history, 'resolve_current_user', lambda: (7, None))
    monkeypatch.setattr(version_history, 'session_is_owned', lambda *_args: True)
    snapshot = {'money-market': {'cleanedData': [{'Principal': 1000}]}}
    monkeypatch.setattr(version_history, 'get_version_by_id', lambda _version_id: {
        'sessionId': 'session-1',
        'versionNumber': 2,
        'dataset_snapshot': snapshot,
    })

    response = app.test_client().post('/api/version/17/restore')

    assert response.status_code == 200
    assert response.get_json()['success'] is True
    assert connection.committed
    assert not connection.rolled_back
    update_query, update_params = cursor.statements[0]
    assert 'UPDATE ui_sessions' in update_query
    assert update_params[0] == update_params[1]
    assert '"Principal": 1000' in update_params[0]


def test_session_delete_removes_session_reports_in_same_transaction(monkeypatch):
    cursor = FakeCursor(rows=[{'file_path': None}])
    connection = FakeConnection(cursor)
    install_db(monkeypatch, sessions, connection)
    monkeypatch.setattr(sessions, 'resolve_current_user', lambda: (7, None))
    monkeypatch.setattr(sessions, 'session_is_owned', lambda *_args, **_kwargs: True)

    response = app.test_client().post(
        '/api/sessions/delete', json={'session_id': 'session-1'}
    )

    assert response.status_code == 200
    assert response.get_json()['success'] is True
    assert connection.committed
    assert not connection.rolled_back
    assert any(
        'DELETE FROM reports WHERE session_id = %s AND user_id = %s' in query
        for query, _params in cursor.statements
    )


def test_migration_runner_records_already_applied_schema(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(migrate, '_schema_is_applied', lambda _cursor: True)

    outcome = migrate.apply_persistence_migration(connection)

    assert outcome == 'recorded_existing_schema'
    assert connection.committed
    assert any(
        'INSERT INTO application_schema_migrations' in query
        for query, _params in cursor.statements
    )
    assert not any(
        query.lstrip().startswith('ALTER TABLE')
        for query, _params in cursor.statements
    )
