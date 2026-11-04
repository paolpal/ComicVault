from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from app.services.scanner import OptimizedComicScanner


def setup_scanner(tmp_path, comics):
    mongo = MagicMock()
    settings = mongo.db['library_settings']
    storage = {}
    settings.find_one.side_effect = lambda _: storage.get('record')
    settings.insert_one.side_effect = lambda record: storage.update(record=record)
    scanner = OptimizedComicScanner(str(tmp_path), mongo)
    scanner.comic_repo.list_all = MagicMock(return_value=comics)
    scanner.comic_repo.get_by_path = MagicMock(return_value=None)
    scanner.comic_repo.delete = MagicMock()
    return scanner


def test_deleted_folder_is_removed_after_successful_scan(tmp_path):
    existing = tmp_path / 'existing'
    existing.mkdir()
    missing = SimpleNamespace(id='removed', title='Removed', path=str(tmp_path / 'removed'))
    present = SimpleNamespace(id='kept', title='Kept', path=str(existing), content_hash='same')
    scanner = setup_scanner(tmp_path, [present, missing])
    scanner.comic_repo.get_by_path.return_value = present
    from app.utils import calculate_comic_hash
    present.content_hash = calculate_comic_hash(str(existing))
    scanner.scan_and_register_comics()
    scanner.comic_repo.delete.assert_called_once_with('removed')


def test_disconnected_empty_library_preserves_catalogue(tmp_path):
    missing = SimpleNamespace(id='kept', title='Kept', path=str(tmp_path / 'comic'))
    scanner = setup_scanner(tmp_path, [missing])
    with pytest.raises(RuntimeError, match='non riconosciuta'):
        scanner.scan_and_register_comics()
    scanner.comic_repo.delete.assert_not_called()


def test_missing_marker_prevents_deletion(tmp_path):
    missing = SimpleNamespace(id='kept', title='Kept', path=str(tmp_path / 'comic'))
    scanner = setup_scanner(tmp_path, [missing])
    scanner.comic_repo.mongo.db['library_settings'].find_one.side_effect = None
    scanner.comic_repo.mongo.db['library_settings'].find_one.return_value = {'marker': 'expected'}
    with pytest.raises(RuntimeError, match='identificativo del disco mancante'):
        scanner.scan_and_register_comics()
    scanner.comic_repo.delete.assert_not_called()


def test_failed_comic_scan_preserves_missing_entries(tmp_path):
    present_dir = tmp_path / 'present'
    present_dir.mkdir()
    missing = SimpleNamespace(id='kept', title='Kept', path=str(tmp_path / 'missing'))
    present = SimpleNamespace(id='present', title='Present', path=str(present_dir), content_hash='old')
    scanner = setup_scanner(tmp_path, [missing, present])
    scanner.comic_repo.get_by_path.return_value = present
    scanner._process_comic_with_hash = MagicMock(side_effect=OSError('unreadable'))
    with pytest.raises(RuntimeError, match='Scansione incompleta'):
        scanner.scan_and_register_comics()
    scanner.comic_repo.delete.assert_not_called()


def test_failed_chapter_read_leaves_existing_record_unchanged(tmp_path):
    folder = tmp_path / 'comic'
    folder.mkdir()
    comic = SimpleNamespace(id='507f1f77bcf86cd799439011', title='Comic', path=str(folder))
    scanner = setup_scanner(tmp_path, [comic])
    scanner.comic_repo.get_by_path.return_value = comic
    scanner._process_chapters_with_hash = MagicMock(side_effect=OSError('unreadable'))
    with pytest.raises(OSError):
        scanner._process_comic_with_hash(str(folder), 'hash')
    collection = scanner.comic_repo.mongo.db['comics']
    collection.update_one.assert_not_called()
    collection.insert_one.assert_not_called()
    scanner.comic_repo.delete.assert_not_called()


def test_updated_comic_keeps_its_identifier(tmp_path):
    folder = tmp_path / 'comic'
    folder.mkdir()
    comic = SimpleNamespace(id='507f1f77bcf86cd799439011', title='Comic', path=str(folder))
    scanner = setup_scanner(tmp_path, [comic])
    scanner.comic_repo.get_by_path.return_value = comic
    scanner._process_chapters_with_hash = MagicMock()
    scanner._process_comic_with_hash(str(folder), 'hash')
    query = scanner.comic_repo.mongo.db['comics'].update_one.call_args.args[0]
    assert query == {'_id': comic.id}
    scanner.comic_repo.delete.assert_not_called()
