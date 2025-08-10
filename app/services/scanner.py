# app/services/scanner.py

import os
from app.models import Comic, Chapter
from app.utils import allowed_file, list_images, extract_metadata_from_filename, load_json, generate_slug
from app.repositories.mongo.chapter import ChapterRepository
from app.repositories.mongo.comic import ComicRepository

class ComicScanner:
    def __init__(self, root_path, mongo):
        """
        :param root_path: Directory principale dove risiedono i fumetti
        :param mongo: Oggetto MongoDB di Flask
        """
        self.root_path = root_path
        self.comic_repo = ComicRepository(mongo)
        self.chapter_repo = ChapterRepository(mongo)

    def scan_and_register_comics(self):
        """Scansiona tutti i fumetti nella directory principale"""
        self.comic_repo.drop()  # Pulisce i fumetti esistenti
        self.chapter_repo.drop()  # Pulisce i capitoli esistenti

        for comic_folder in os.listdir(self.root_path):
            comic_path = os.path.join(self.root_path, comic_folder)
            if os.path.isdir(comic_path):
                self._process_comic(comic_path)

    def _process_comic(self, comic_path):
        """Processa un singolo fumetto"""
        comic_id = os.path.basename(comic_path)

        metadata_path = os.path.join(comic_path, "metadata.json")
        if os.path.exists(metadata_path):
            metadata = load_json(metadata_path)
        else:
            metadata = extract_metadata_from_filename(comic_id)

        comic = Comic(
            title=metadata.get("title", comic_id),
            original_title=metadata.get("original_title"),
            author=metadata.get("author"),
            plot=metadata.get("plot"),
            year=metadata.get("year"),
            genres=metadata.get("genres", []),
            status=metadata.get("status"),
            language=metadata.get("language", None),
            cover=metadata.get("cover"),
            tags=metadata.get("tags", []),
            version=metadata.get("version", None),
            path=comic_path
        )
        saved_comic_id = self.comic_repo.save(comic)

        # Scansiona sottocartelle (capitoli o volumi)
        for entry in os.listdir(comic_path):
            entry_path = os.path.join(comic_path, entry)
            if not os.path.isdir(entry_path):
                continue

            if self._is_chapter_directory(entry_path):
                self._register_chapter(entry_path, saved_comic_id)
            else:
                # Assume che sia una cartella volume
                self._process_volume(entry_path, saved_comic_id)

    def _process_volume(self, volume_path, comic_id):
        """Processa i capitoli dentro una cartella volume"""
        for chapter_folder in os.listdir(volume_path):
            chapter_path = os.path.join(volume_path, chapter_folder)
            if os.path.isdir(chapter_path):
                volume_folder = os.path.basename(volume_path)
                self._register_chapter(chapter_path, comic_id, volume_folder)

    def _is_chapter_directory(self, path):
        """Determina se una directory contiene immagini o metadati"""
        has_images = any(allowed_file(f, {'jpg', 'jpeg', 'png'}) for f in os.listdir(path))
        has_metadata = os.path.exists(os.path.join(path, "metadata.json"))
        return has_images or has_metadata

    def _register_chapter(self, chapter_path, comic_id, volume_folder=None):
        """Registra un singolo capitolo"""
        metadata_path = os.path.join(chapter_path, "metadata.json")
        if os.path.exists(metadata_path):
            metadata = load_json(metadata_path)
            chapter_number = metadata.get("number", self._extract_chapter_number(chapter_path))
            chapter_title = metadata.get("title", f"Chapter {chapter_number}")
            page_count = metadata.get("page_count", None)
            language = metadata.get("language")
            publication_date = metadata.get("publication_date")
            rtl = metadata.get("rtl", True)
        else:
            chapter_number = self._extract_chapter_number(chapter_path)
            chapter_title = f"Chapter {chapter_number}"
            page_count = len(list_images(chapter_path))
            language = "unknown"
            publication_date = None
            rtl = True
        page_count = page_count if page_count is not None else len(list_images(chapter_path))

        chapter_path = os.path.join(volume_folder, os.path.basename(chapter_path)) if volume_folder else os.path.basename(chapter_path)

        chapter = Chapter(
            comic_id=comic_id,
            number=chapter_number,
            title=chapter_title,
            filename=chapter_path,
            page_count=page_count,
            language=language,
            publication_date=publication_date,
            is_archive=False,
            rtl=rtl
        )
        self.chapter_repo.save(chapter)

    def _extract_chapter_number(self, name):
        base = os.path.basename(name)
        try:
            return int(''.join(filter(str.isdigit, base)))
        except ValueError:
            return 0
