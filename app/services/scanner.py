# app/services/scanner.py

import os
import logging
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
        comics_removed = 0
        
        # Prima rimuovi i fumetti che non esistono più sul filesystem
        comics_removed = self._remove_deleted_comics()
        
        for comic_folder in os.listdir(self.root_path):
            comic_path = os.path.join(self.root_path, comic_folder)
            if os.path.isdir(comic_path):
                try:
                    # Calcola hash del fumetto
                    current_hash = calculate_comic_hash(comic_path)
                    self.logger.info(f"Hash del fumetto {comic_folder}: {current_hash}")

                    # Controlla se il fumetto esiste già nel database
                    existing_comic = self.comic_repo.get_by_path(comic_path)
                    
                    if not existing_comic or existing_comic.content_hash != current_hash:
                        self.logger.info(f"Processando fumetto modificato: {comic_folder}")
                        self._process_comic_with_hash(comic_path, current_hash)
                        comics_processed += 1
                    else:
                        self.logger.debug(f"Saltando fumetto non modificato: {comic_folder}")
                        comics_skipped += 1
                        
                except Exception as e:
                    self.logger.error(f"Errore nel processare {comic_folder}: {e}")
                    # Fallback: processa comunque il fumetto
                    self._process_comic(comic_path)
                    comics_processed += 1
        
        self.logger.info(f"Scansione completata: {comics_processed} processati, {comics_skipped} saltati, {comics_removed} rimossi")

    def _remove_deleted_comics(self):
        """Rimuove dal database i fumetti che non esistono più sul filesystem"""
        removed_count = 0
        
        # Ottieni tutti i fumetti dal database
        all_comics = list(self.comic_repo.list_all())
        
        for comic in all_comics:
            comic_path = comic.path
            if comic_path and not os.path.exists(comic_path) and comic.id is not None:
                self.logger.info(f"Rimuovendo fumetto eliminato dal filesystem: {comic.title} ({comic_path})")
                
                # Rimuovi prima tutti i capitoli del fumetto
                self.chapter_repo.delete_by_comic_id(comic.id)
                
                # Poi rimuovi il fumetto stesso
                self.comic_repo.delete(comic.id)
                
                removed_count += 1
        
        if removed_count > 0:
            self.logger.info(f"Rimossi {removed_count} fumetti eliminati dal filesystem")
        
        return removed_count

    def _process_comic_with_hash(self, comic_path, content_hash):
        """Processa un fumetto aggiornando solo i capitoli modificati"""
        comic_id = os.path.basename(comic_path)

        # Rimuovi il fumetto esistente e i suoi capitoli se presente
        existing_comic = self.comic_repo.get_by_path(comic_path)
        if existing_comic and existing_comic.id is not None:
            self.chapter_repo.delete_by_comic_id(existing_comic.id)
            self.comic_repo.delete(existing_comic.id)

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

        logger.info(f"Registrando fumetto: {comic.title} con hash {content_hash}")
        saved_comic_id = self.comic_repo.save(comic)

        # Estrai il valore RTL di default del fumetto
        comic_rtl_default = metadata.get("rtl", True)

        # Processa capitoli con hash individuali
        self._process_chapters_with_hash(comic_path, saved_comic_id, comic_rtl_default)

    def _process_chapters_with_hash(self, comic_path, comic_id, comic_rtl_default):
        """Processa i capitoli calcolando hash individuali"""
        for entry in os.listdir(comic_path):
            entry_path = os.path.join(comic_path, entry)
            
            # Controlla se è un file archivio singolo
            if os.path.isfile(entry_path) and self._is_archive_file(entry):
                chapter_hash = calculate_chapter_hash(entry_path, is_archive=True)
                self._register_archive_chapter_with_hash(entry_path, comic_id, comic_rtl_default, chapter_hash)
            elif os.path.isdir(entry_path):
                if self._is_chapter(entry_path):
                    chapter_hash = calculate_chapter_hash(entry_path, is_archive=False)
                    self._register_chapter_with_hash(entry_path, comic_id, comic_rtl_default, chapter_hash)
                else:
                    # Assume che sia una cartella volume
                    self._process_volume_with_hash(entry_path, comic_id, comic_rtl_default)

    def _process_volume_with_hash(self, volume_path, comic_id, comic_rtl_default):
        """Processa i capitoli dentro una cartella volume con hash"""
        volume_folder = os.path.basename(volume_path)
        
        for entry in os.listdir(volume_path):
            entry_path = os.path.join(volume_path, entry)
            
            if os.path.isfile(entry_path) and self._is_archive_file(entry):
                chapter_hash = calculate_chapter_hash(entry_path, is_archive=True)
                self._register_archive_chapter_with_hash(entry_path, comic_id, comic_rtl_default, chapter_hash, volume_folder)
            elif os.path.isdir(entry_path):
                chapter_hash = calculate_chapter_hash(entry_path, is_archive=False)
                self._register_chapter_with_hash(entry_path, comic_id, comic_rtl_default, chapter_hash, volume_folder)

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
