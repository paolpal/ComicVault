# app/services/scanner.py

import os
from app.models import Comic, Chapter
from app.utils import allowed_file, list_images, extract_metadata_from_filename

class ComicScanner:
    def __init__(self, directory_path, mongo):
        """
        Inizializza il ComicScanner con i dettagli della directory e l'oggetto MongoDB esistente.

        :param directory_path: Percorso della directory da scansionare
        :param mongo: Oggetto MongoDB fornito da Flask
        """
        self.directory_path = directory_path
        self.db = mongo.db
        self.comics_collection = self.db.comics

    def scan_and_register_comics(self):
        """
        Scansiona la directory e registra i fumetti e i capitoli trovati nel database.
        """
        self.comics_collection.drop()
        for entry in os.listdir(self.directory_path):
            entry_path = os.path.join(self.directory_path, entry)
            if os.path.isdir(entry_path):
                self._process_comic_directory(entry_path)

    def _process_comic_directory(self, comic_directory):
        """
        Processa una directory come un fumetto e i suoi contenuti come capitoli.

        :param comic_directory: Percorso della directory del fumetto
        """
        comic_title = os.path.basename(comic_directory)
        metadata = extract_metadata_from_filename(comic_title)
        comic = Comic(title=metadata['title'], path=comic_directory)
        comic_id = comic.save()

        for entry in os.listdir(comic_directory):
            chapter_path = os.path.join(comic_directory, entry)
            if os.path.isdir(chapter_path):
                # Capitolo come directory
                self._process_directory_as_chapter(chapter_path, comic_id)
            elif allowed_file(entry, {'zip', 'cbz', 'rar', 'cbr'}):
                # Capitolo come archivio
                self._process_archive_as_chapter(chapter_path, comic_id)

    def _process_directory_as_chapter(self, chapter_directory, comic_id):
        """
        Processa una directory come un capitolo del fumetto.

        :param chapter_directory: Percorso della directory del capitolo
        :param comic_id: ID del fumetto a cui appartiene il capitolo
        """
        chapter_filename = os.path.basename(chapter_directory)
        chapter_number = self._extract_chapter_number(chapter_filename)
        chapter_title = 'Chapter '+str(chapter_number)
        chapter_is_archive = False

        # Ottieni il numero di pagine contandole nella directory
        page_files = list_images(chapter_directory, chapter_is_archive)
        page_count = len(page_files)

        # Salva il capitolo nel database
        chapter = Chapter(
            comic_id=comic_id,
            title=chapter_title,
            number=chapter_number,
            filename=chapter_filename,
            page_count=page_count,
            is_archive=chapter_is_archive
        )
        chapter.save()

    def _process_archive_as_chapter(self, archive_path, comic_id):
        """
        Processa un archivio come un capitolo del fumetto.

        :param archive_path: Percorso dell'archivio
        :param comic_id: ID del fumetto a cui appartiene il capitolo
        """
        chapter_filename = os.path.basename(archive_path)
        chapter_number = self._extract_chapter_number(chapter_filename)
        chapter_title = 'Chapter '+str(chapter_number)
        chapter_is_archive = True

        # Ottieni il numero di pagine contandole nella directory
        page_files = list_images(archive_path, chapter_is_archive)
        page_count = len(page_files)

        # Salva il capitolo nel database
        chapter = Chapter(
            comic_id=comic_id,
            title=chapter_title,
            number=chapter_number,
            filename=chapter_filename,
            page_count=page_count,
            is_archive=chapter_is_archive
        )
        chapter.save()

    def _extract_chapter_number(self, chapter_name):
        """
        Estrae il numero del capitolo dal nome del capitolo, se disponibile.

        :param chapter_name: Nome del capitolo
        :return: Numero del capitolo come intero, o 0 se non trovato
        """
        try:
            return int(''.join(filter(str.isdigit, chapter_name)))
        except ValueError:
            return 0
