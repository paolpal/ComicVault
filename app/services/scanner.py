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

        # Estrai il valore RTL di default del fumetto (default: True)
        comic_rtl_default = metadata.get("rtl", True)

        # Scansiona contenuto della directory del fumetto
        for entry in os.listdir(comic_path):
            entry_path = os.path.join(comic_path, entry)
            
            # Controlla se è un file archivio singolo
            if os.path.isfile(entry_path) and self._is_archive_file(entry):
                self._register_archive_chapter(entry_path, saved_comic_id, comic_rtl_default)
            elif os.path.isdir(entry_path):
                if self._is_chapter(entry_path):
                    self._register_chapter(entry_path, saved_comic_id, comic_rtl_default)
                else:
                    # Assume che sia una cartella volume
                    self._process_volume(entry_path, saved_comic_id, comic_rtl_default)

    def _process_volume(self, volume_path, comic_id, comic_rtl_default):
        """Processa i capitoli dentro una cartella volume"""
        volume_folder = os.path.basename(volume_path)
        
        for entry in os.listdir(volume_path):
            entry_path = os.path.join(volume_path, entry)
            
            # Gestisce sia directory che file archivio
            if os.path.isfile(entry_path) and self._is_archive_file(entry):
                self._register_archive_chapter(entry_path, comic_id, comic_rtl_default, volume_folder)
            elif os.path.isdir(entry_path):
                self._register_chapter(entry_path, comic_id, comic_rtl_default, volume_folder)

    def _is_chapter(self, path):
        """Determina se una directory contiene immagini o metadati"""
        has_images = any(allowed_file(f, {'jpg', 'jpeg', 'png'}) for f in os.listdir(path))
        has_metadata = os.path.exists(os.path.join(path, "metadata.json"))
        is_archive = any(f.lower().endswith(('.cbz', '.cbr', '.zip', '.rar')) for f in os.listdir(path))
        return has_images or has_metadata or is_archive

    def _is_archive_file(self, filename):
        """Determina se un file è un archivio di fumetti supportato"""
        return filename.lower().endswith(('.cbz', '.cbr', '.zip', '.rar'))

    def _register_chapter(self, chapter_path, comic_id, comic_rtl_default, volume_folder=None):
        """Registra un singolo capitolo da directory"""
        metadata_path = os.path.join(chapter_path, "metadata.json")
        if os.path.exists(metadata_path):
            metadata = load_json(metadata_path)
            chapter_number = metadata.get("number", self._extract_chapter_number(chapter_path))
            chapter_title = metadata.get("title", f"Chapter {chapter_number}")
            page_count = metadata.get("page_count", None)
            language = metadata.get("language")
            publication_date = metadata.get("publication_date")
            # RTL: usa quello del capitolo se specificato, altrimenti quello del fumetto
            rtl = metadata.get("rtl", comic_rtl_default)
        else:
            chapter_number = self._extract_chapter_number(chapter_path)
            chapter_title = f"Chapter {chapter_number}"
            page_count = None
            language = "unknown"
            publication_date = None
            # Se non ci sono metadati, usa quello del fumetto
            rtl = comic_rtl_default
        
        # Conta le pagine se non specificato nei metadati
        if page_count is None:
            page_count = len(list_images(chapter_path, is_archive=False))

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

    def _register_archive_chapter(self, archive_path, comic_id, comic_rtl_default, volume_folder=None):
        """Registra un capitolo da un file archivio (CBZ, CBR, ZIP, RAR)"""
        # Estrai il numero del capitolo dal nome del file
        archive_name = os.path.basename(archive_path)
        chapter_number = self._extract_chapter_number(archive_name)
        chapter_title = f"Chapter {chapter_number}"
        
        # Conta le pagine nell'archivio
        try:
            page_count = len(list_images(archive_path, is_archive=True))
        except Exception as e:
            print(f"Errore nel contare le pagine dell'archivio {archive_path}: {e}")
            page_count = 0
        
        # Usa il nome del file come filename (relativo se in un volume)
        filename = os.path.join(volume_folder, archive_name) if volume_folder else archive_name
        
        chapter = Chapter(
            comic_id=comic_id,
            number=chapter_number,
            title=chapter_title,
            filename=filename,
            page_count=page_count,
            language="unknown",
            publication_date=None,
            is_archive=True,  # Importante: marca come archivio
            rtl=comic_rtl_default  # Usa il valore RTL del fumetto per gli archivi
        )
        self.chapter_repo.save(chapter)

    def _extract_chapter_number(self, name):
        base = os.path.basename(name)
        try:
            return int(''.join(filter(str.isdigit, base)))
        except ValueError:
            return 0
