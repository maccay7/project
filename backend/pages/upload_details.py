
import os
import json
import base64
import uuid
from utils.db import get_db


def parse_upload_file(file_storage):
    binary = file_storage.read()
    return base64.b64encode(binary).decode('utf-8')


def clean_data(data, options):
    seen = set()
    cleaned = []
    duplicates = 0
    missing = 0

    for row in data:
        row_copy = {k: ('' if v is None else v) for k, v in (row or {}).items()}
        row_key = json.dumps(row_copy, sort_keys=True)
        if row_key in seen:
            duplicates += 1
            continue
        seen.add(row_key)

        for key, value in row_copy.items():
            if value is None or value == '':
                row_copy[key] = options.get('fill_missing', '')
                missing += 1

        cleaned.append(row_copy)

    return cleaned, {
        'duplicates_removed': duplicates,
        'missing_values_filled': missing
    }


def save_dataset(name, file_base64='', sheet_names=None, upload_id=None, data=None, headers=None, instrument_type=None):
    conn = get_db()
    if not conn:
        return None
    try:
        ds_id = upload_id or str(uuid.uuid4())
        cursor = conn.cursor()
        # Store JSON fields as JSON strings
        cursor.execute(
            "REPLACE INTO datasets (id, name, file_base64, data, headers, instrument_type, upload_status, done) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                ds_id,
                name,
                file_base64,
                json.dumps(data) if data is not None else None,
                json.dumps(headers) if headers is not None else None,
                instrument_type,
                'uploaded',
                False
            )
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {'id': ds_id, 'name': name, 'file_base64': file_base64, 'data': data, 'headers': headers, 'instrument_type': instrument_type}
    except Exception as e:
        print(f"Save dataset error: {e}")
        return None


def get_saved_datasets():
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, JSON_LENGTH(data) as rows, instrument_type, done, created_at FROM datasets WHERE done = FALSE ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            {
                'id': r.get('id'),
                'name': r.get('name'),
                'rows': r.get('rows') or 0,
                'instrument_type': r.get('instrument_type'),
                'done': bool(r.get('done'))
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Get datasets error: {e}")
        return []


def load_saved_dataset(dataset_id):
    if not dataset_id:
        return None
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM datasets WHERE id = %s", (dataset_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return None
        data = row.get('data')
        try:
            data = json.loads(data) if isinstance(data, str) else data
        except Exception:
            data = None
        headers = row.get('headers')
        try:
            headers = json.loads(headers) if isinstance(headers, str) else headers
        except Exception:
            headers = None
        return {
            'id': row.get('id'),
            'name': row.get('name'),
            'file_base64': row.get('file_base64'),
            'data': data,
            'headers': headers,
            'instrument_type': row.get('instrument_type'),
            'done': bool(row.get('done'))
        }
    except Exception as e:
        print(f"Load dataset error: {e}")
        return None


def delete_saved_dataset(dataset_id):
    if not dataset_id:
        return False
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Delete dataset error: {e}")
        return False


def mark_dataset_done(dataset_id, done=True):
    if not dataset_id:
        return False
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE datasets SET done = %s WHERE id = %s", (1 if done else 0, dataset_id))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Mark done error: {e}")
        return False
