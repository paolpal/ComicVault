import subprocess
import sys
import threading
from unittest.mock import patch

from pymongo.errors import DuplicateKeyError

from app import app
from app.services.scan_lock import acquire_scan_lock


def test_lock_is_shared_between_processes_and_released():
    lock = acquire_scan_lock()
    assert lock is not None
    try:
        result = subprocess.run(
            [sys.executable, '-c',
             'from app.services.scan_lock import acquire_scan_lock; '
             'raise SystemExit(0 if acquire_scan_lock() is None else 1)'],
            capture_output=True, timeout=10,
        )
        assert result.returncode == 0, result.stderr.decode()
    finally:
        lock.close()
    lock = acquire_scan_lock()
    assert lock is not None
    lock.close()


def test_scan_request_does_not_start_second_scan():
    started = threading.Event()
    finish = threading.Event()
    done = threading.Event()

    def scan():
        started.set()
        try:
            assert finish.wait(5)
        finally:
            done.set()

    with patch('app.controllers.mongo') as mongo, \
         patch('app.controllers.OptimizedComicScanner') as scanner:
        scanner.return_value.scan_and_register_comics.side_effect = scan
        client = app.test_client()
        try:
            first = client.get('/scan')
            assert started.wait(5)
            second = client.get('/scan')
            assert 'scan=started' in first.location
            assert 'scan=running' in second.location
            assert scanner.call_count == 1
            mongo.db['comics'].create_index.assert_called_once_with(
                'path', unique=True, name='unique_comic_path')
        finally:
            finish.set()
            assert done.wait(5)


def test_existing_duplicates_stop_scan_and_release_lock():
    with patch('app.controllers.mongo') as mongo, \
         patch('app.controllers.OptimizedComicScanner') as scanner:
        mongo.db['comics'].create_index.side_effect = DuplicateKeyError('duplicate path')
        response = app.test_client().get('/scan')
        assert response.status_code == 409
        scanner.assert_not_called()
    lock = acquire_scan_lock()
    assert lock is not None
    lock.close()
