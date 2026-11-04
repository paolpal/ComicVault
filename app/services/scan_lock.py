"""Coordinate scans across Gunicorn workers in the same container."""
import fcntl
import os
import tempfile


def acquire_scan_lock():
    path = os.path.join(tempfile.gettempdir(), "comicvault-scan.lock")
    lock = open(path, "a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return None
    except BaseException:
        lock.close()
        raise
    return lock
