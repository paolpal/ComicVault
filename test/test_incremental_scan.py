import json
from unittest.mock import MagicMock, patch

from app.models import Comic
from app.services.scanner import OptimizedComicScanner


def write_chapter(folder, number, title):
    folder.mkdir(exist_ok=True)
    (folder / 'metadata.json').write_text(json.dumps({'number': str(number), 'seqNumber': number, 'title': title}))
    (folder / '1.jpg').write_bytes(b'image')


def test_reuses_unchanged_chapters_and_reconciles_changes(tmp_path):
    comic_dir = tmp_path / 'comic'
    comic_dir.mkdir()
    write_chapter(comic_dir / 'chapter_1', 1, 'First')
    write_chapter(comic_dir / 'chapter_2', 2, 'Second')
    write_chapter(comic_dir / 'chapter_3', 3, 'Third')
    mongo = MagicMock()
    scanner = OptimizedComicScanner(str(tmp_path), mongo)
    scanner.comic_repo.get_by_path = MagicMock(return_value=None)
    scanner._process_comic_with_hash(str(comic_dir), 'first-hash')
    document = mongo.db['comics'].insert_one.call_args.args[0]
    comic = Comic(**document)
    scanner.comic_repo.get_by_path.return_value = comic

    write_chapter(comic_dir / 'chapter_2', 2, 'Changed')
    import shutil
    shutil.rmtree(comic_dir / 'chapter_3')
    write_chapter(comic_dir / 'chapter_4', 4, 'Fourth')
    with patch.object(scanner, '_register_chapter_with_hash', wraps=scanner._register_chapter_with_hash) as register:
        scanner._process_comic_with_hash(str(comic_dir), 'second-hash')
    assert register.call_count == 2
    query, update = mongo.db['comics'].update_one.call_args.args
    assert query['_id'] == document['_id']
    chapters = {item['filename']: item for item in update['$set']['chapters']}
    assert set(chapters) == {'chapter_1', 'chapter_2', 'chapter_4'}
    assert chapters['chapter_1'] == document['chapters'][0] or chapters['chapter_1'] in document['chapters']
    assert chapters['chapter_2']['title'] == 'Changed'
    assert chapters['chapter_4']['title'] == 'Fourth'


def test_default_rtl_change_reprocesses_unchanged_chapters(tmp_path):
    comic_dir = tmp_path / 'comic'
    comic_dir.mkdir()
    metadata = comic_dir / 'metadata.json'
    metadata.write_text(json.dumps({'title': 'Comic', 'rtl': True}))
    write_chapter(comic_dir / 'chapter_1', 1, 'First')
    mongo = MagicMock()
    scanner = OptimizedComicScanner(str(tmp_path), mongo)
    scanner.comic_repo.get_by_path = MagicMock(return_value=None)
    scanner._process_comic_with_hash(str(comic_dir), 'first')
    scanner.comic_repo.get_by_path.return_value = Comic(**mongo.db['comics'].insert_one.call_args.args[0])
    metadata.write_text(json.dumps({'title': 'Comic', 'rtl': False}))
    scanner._process_comic_with_hash(str(comic_dir), 'second')
    assert mongo.db['comics'].update_one.call_args.args[1]['$set']['chapters'][0]['rtl'] is False
