# app/services/scanner.py

import os
import logging
import uuid
from bson import ObjectId
from app.models import Comic, Chapter
from app.utils import allowed_file, list_images, extract_metadata_from_filename, load_json, generate_slug, calculate_comic_hash, calculate_chapter_hash
from app.repositories.mongo.chapter import ChapterRepository
from app.repositories.mongo.comic import ComicRepository

logger = logging.getLogger(__name__)

class ComicScanner:
    def __init__(self, root_path, mongo):
        """
        :param root_path: Directory principale dove risiedono i fumetti
        :param mongo: Oggetto MongoDB di Flask
        """
        self.logger = logging.getLogger(self.__class__.__name__)
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
            original_title=metadata.get("originalTitle", ""),
            author=metadata.get("author", ""),
            plot=metadata.get("plot", ""),
            year=metadata.get("year", ""),
            genres=metadata.get("genres", []),
            status=metadata.get("status", ""),
            language=metadata.get("language", ""),
            cover=metadata.get("cover", ""),
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
            seq_number = float(metadata.get("seqNumber", chapter_number))
            chapter_title = metadata.get("title", f"Chapter {chapter_number}")
            page_count = metadata.get("pageCount", None)
            language = metadata.get("language")
            publication_date = metadata.get("publicationDate")
            # RTL: usa quello del capitolo se specificato, altrimenti quello del fumetto
            rtl = metadata.get("rtl", comic_rtl_default)
        else:
            chapter_number = self._extract_chapter_number(chapter_path)
            seq_number = float(chapter_number)
            page_count = None
            chapter_title = f"Chapter {chapter_number}"
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
            seq_number=seq_number,
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
            self.logger.error(f"Errore nel contare le pagine dell'archivio {archive_path}: {e}")
            page_count = 0
        
        # Usa il nome del file come filename (relativo se in un volume)
        filename = os.path.join(volume_folder, archive_name) if volume_folder else archive_name
        
        chapter = Chapter(
            comic_id=comic_id,
            number=chapter_number,
            seq_number=float(chapter_number),
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


class OptimizedComicScanner(ComicScanner):
    """
    Scanner ottimizzato che utilizza hash per processare solo i fumetti modificati.
    """
    
    def __init__(self, root_path, mongo):
        super().__init__(root_path, mongo)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def scan_and_register_comics(self):
        """Scansiona solo i fumetti modificati usando hash"""
        self.logger.info("Avvio scansione ottimizzata con meccanismo hash...")
        
        comics_processed = 0
        comics_skipped = 0
        errors = []

        # A missing or unreadable library must never be treated as an empty one.
        comic_folders = os.listdir(self.root_path)
        known_comics = self.comic_repo.list_all()
        marker = self._verify_library(comic_folders, known_comics)
        for comic_folder in comic_folders:
            comic_path = os.path.join(self.root_path, comic_folder)
            if os.path.isdir(comic_path):
                try:
                    current_hash = calculate_comic_hash(comic_path, strict=True)
                    existing_comic = self.comic_repo.get_by_path(comic_path)
                    if not existing_comic or existing_comic.content_hash != current_hash:
                        self._process_comic_with_hash(comic_path, current_hash)
                        comics_processed += 1
                    else:
                        comics_skipped += 1
                except Exception:
                    self.logger.exception("Errore nel processare %s", comic_folder)
                    errors.append(comic_folder)

        if errors:
            raise RuntimeError("Scansione incompleta: impossibile leggere " + ", ".join(errors))

        # Re-read the marker and the directory before deleting anything.
        current_folders = os.listdir(self.root_path)
        if self._verify_library(current_folders, known_comics) != marker:
            raise RuntimeError("La libreria è cambiata durante la scansione.")
        if set(current_folders) - {".comicvault-library-id"} != set(comic_folders) - {".comicvault-library-id"}:
            raise RuntimeError("La libreria è cambiata durante la scansione; riprova.")
        missing = []
        for comic in known_comics:
            if not comic.path or comic.id is None:
                continue
            try:
                os.stat(comic.path)
            except FileNotFoundError:
                missing.append(comic)
        # Check every path before removing any records; other filesystem errors
        # abort the scan and leave the catalog untouched.
        removed = 0
        for comic in missing:
            self.comic_repo.delete(comic.id)
            removed += 1
        self.logger.info("Scansione completata: %s processati, %s saltati, %s rimossi", comics_processed, comics_skipped, removed)

    def _verify_library(self, entries, known_comics):
        """Identify the mounted library before permitting destructive reconciliation."""
        marker_path = os.path.join(self.root_path, ".comicvault-library-id")
        settings = self.comic_repo.mongo.db["library_settings"]
        record = settings.find_one({"_id": "library"})
        if record:
            try:
                with open(marker_path, encoding="utf-8") as marker_file:
                    marker = marker_file.read().strip()
            except OSError as exc:
                raise RuntimeError("Libreria non disponibile: identificativo del disco mancante.") from exc
            if marker != record["marker"]:
                raise RuntimeError("Libreria non disponibile: identificativo del disco non corrispondente.")
            return marker

        # Never initialise a different, empty mount over an existing catalogue.
        if known_comics and not any(os.path.exists(comic.path) for comic in known_comics if comic.path):
            raise RuntimeError("Libreria non riconosciuta: nessun fumetto del catalogo è raggiungibile.")
        if os.path.exists(marker_path):
            with open(marker_path, encoding="utf-8") as marker_file:
                marker = marker_file.read().strip()
            if not marker:
                raise RuntimeError("Identificativo della libreria vuoto.")
        else:
            marker = uuid.uuid4().hex
            with open(marker_path, "x", encoding="utf-8") as marker_file:
                marker_file.write(marker)
        settings.insert_one({"_id": "library", "marker": marker})
        return marker

    def _process_comic_with_hash(self, comic_path, content_hash):
        """Processa un fumetto aggiornando solo i capitoli modificati"""
        comic_id = os.path.basename(comic_path)

        existing_comic = self.comic_repo.get_by_path(comic_path)

        # Carica metadati del fumetto
        metadata_path = os.path.join(comic_path, "metadata.json")
        if os.path.exists(metadata_path):
            metadata = load_json(metadata_path)
        else:
            metadata = extract_metadata_from_filename(comic_id)

        # Crea nuovo fumetto con hash
        comic = Comic(
            title=metadata.get("title", comic_id),
            original_title=metadata.get("original_title", ""),
            author=metadata.get("author", ""),
            plot=metadata.get("plot", ""),
            year=metadata.get("year", ""),
            genres=metadata.get("genres", []),
            status=metadata.get("status", ""),
            language=metadata.get("language", ""),
            cover=metadata.get("cover", ""),
            tags=metadata.get("tags", []),
            version=metadata.get("version", None),
            path=comic_path,
            content_hash=content_hash
        )

        # Build the entire replacement before changing the database, so a read
        # failure cannot erase the existing catalog entry.
        comic_id = existing_comic.id if existing_comic else ObjectId()
        chapters = []
        rtl_default = metadata.get("rtl", True)
        cached = {}
        if existing_comic and getattr(existing_comic, "scan_rtl_default", None) == rtl_default:
            cached = {chapter.filename: chapter for chapter in existing_comic.chapters}

        class ChapterCollector:
            def save(self, chapter):
                chapters.append(chapter.__dict__.copy())
                return True

        original_repo = self.chapter_repo
        try:
            self.chapter_repo = ChapterCollector()
            self._process_chapters_with_hash(comic_path, comic_id, rtl_default, cached)
        finally:
            self.chapter_repo = original_repo

        comic_data = comic.__dict__.copy()
        comic_data["chapters"] = chapters
        comic_data["scan_rtl_default"] = rtl_default
        if existing_comic:
            self.comic_repo.mongo.db["comics"].update_one(
                {"_id": comic_id}, {"$set": comic_data}
            )
        else:
            comic_data["_id"] = comic_id
            self.comic_repo.mongo.db["comics"].insert_one(comic_data)
        logger.info("Registrato fumetto: %s", comic.title)

    def _process_chapters_with_hash(self, comic_path, comic_id, comic_rtl_default, cached=None):
        """Processa i capitoli calcolando hash individuali"""
        cached = cached or {}
        for entry in os.listdir(comic_path):
            entry_path = os.path.join(comic_path, entry)
            if os.path.isfile(entry_path) and self._is_archive_file(entry):
                self._reconcile_chapter(entry_path, comic_id, comic_rtl_default, cached, is_archive=True)
            elif os.path.isdir(entry_path):
                if self._is_chapter(entry_path):
                    self._reconcile_chapter(entry_path, comic_id, comic_rtl_default, cached)
                else:
                    self._process_volume_with_hash(entry_path, comic_id, comic_rtl_default, cached)

    def _process_volume_with_hash(self, volume_path, comic_id, comic_rtl_default, cached):
        """Processa i capitoli dentro una cartella volume con hash"""
        volume_folder = os.path.basename(volume_path)
        
        for entry in os.listdir(volume_path):
            entry_path = os.path.join(volume_path, entry)
            
            if os.path.isfile(entry_path) and self._is_archive_file(entry):
                self._reconcile_chapter(entry_path, comic_id, comic_rtl_default, cached, volume_folder, is_archive=True)
            elif os.path.isdir(entry_path):
                self._reconcile_chapter(entry_path, comic_id, comic_rtl_default, cached, volume_folder)

    def _reconcile_chapter(self, path, comic_id, rtl_default, cached, volume_folder=None, is_archive=False):
        filename = os.path.join(volume_folder, os.path.basename(path)) if volume_folder else os.path.basename(path)
        chapter_hash = calculate_chapter_hash(path, is_archive=is_archive, strict=True)
        previous = cached.get(filename)
        if previous and previous.content_hash == chapter_hash and previous.is_archive == is_archive:
            self.chapter_repo.save(previous)
        elif is_archive:
            self._register_archive_chapter_with_hash(path, comic_id, rtl_default, chapter_hash, volume_folder)
        else:
            self._register_chapter_with_hash(path, comic_id, rtl_default, chapter_hash, volume_folder)

    def _register_chapter_with_hash(self, chapter_path, comic_id, comic_rtl_default, content_hash, volume_folder=None):
        """Registra un capitolo da directory con hash"""
        metadata_path = os.path.join(chapter_path, "metadata.json")
        if os.path.exists(metadata_path):
            metadata = load_json(metadata_path)
            chapter_number = metadata.get("number", self._extract_chapter_number(chapter_path))
            seq_number = float(metadata.get("seqNumber", chapter_number))
            chapter_title = metadata.get("title", f"Chapter {chapter_number}")
            page_count = metadata.get("page_count", None)
            language = metadata.get("language")
            publication_date = metadata.get("publication_date")
            rtl = metadata.get("rtl", comic_rtl_default)
        else:
            chapter_number = self._extract_chapter_number(chapter_path)
            seq_number = float(chapter_number)
            chapter_title = f"Chapter {chapter_number}"
            page_count = None
            language = "unknown"
            publication_date = None
            rtl = comic_rtl_default
        
        # Conta le pagine se non specificato nei metadati
        if page_count is None:
            page_count = len(list_images(chapter_path, is_archive=False))

        chapter_path = os.path.join(volume_folder, os.path.basename(chapter_path)) if volume_folder else os.path.basename(chapter_path)

        chapter = Chapter(
            comic_id=comic_id,
            number=chapter_number,
            seq_number=seq_number,
            title=chapter_title,
            filename=chapter_path,
            page_count=page_count,
            language=language,
            publication_date=publication_date,
            is_archive=False,
            rtl=rtl,
            content_hash=content_hash
        )
        self.chapter_repo.save(chapter)

    def _register_archive_chapter_with_hash(self, archive_path, comic_id, comic_rtl_default, content_hash, volume_folder=None):
        """Registra un capitolo da archivio con hash"""
        archive_name = os.path.basename(archive_path)
        chapter_number = self._extract_chapter_number(archive_name)
        chapter_title = f"Chapter {chapter_number}"
        
        # Conta le pagine nell'archivio
        try:
            page_count = len(list_images(archive_path, is_archive=True))
        except Exception as e:
            self.logger.error(f"Errore nel contare le pagine dell'archivio {archive_path}: {e}")
            page_count = 0
        
        filename = os.path.join(volume_folder, archive_name) if volume_folder else archive_name
        
        chapter = Chapter(
            comic_id=comic_id,
            number=chapter_number,
            seq_number=float(chapter_number),
            title=chapter_title,
            filename=filename,
            page_count=page_count,
            language="unknown",
            publication_date=None,
            is_archive=True,
            rtl=comic_rtl_default,
            content_hash=content_hash
        )
        self.chapter_repo.save(chapter)
