import os
from flask import abort
from io import BytesIO
import zipfile
import rarfile
from app.models import Comic, Chapter

class ComicService:
    @staticmethod
    def get_page_image(comic_id, chapter_number, page_number):
        """
        Recupera l'immagine di una specifica pagina di un capitolo di un fumetto.

        :param comic_id: ID del fumetto
        :param chapter_number: Numero del capitolo
        :param page_number: Numero della pagina
        :return: Tuple contenente i dati dell'immagine e il mimetype
        """
        # Recupera il fumetto e il capitolo dal database
        comic = Comic.get_by_id(comic_id)
        chapter = Chapter.find_by_number(comic_id, chapter_number)

        if not chapter:
            raise FileNotFoundError("Capitolo non trovato")

        # Controlla se il capitolo è un archivio o una cartella
        if chapter['is_archive']:
            archive_path = os.path.join(comic['path'], chapter['filename'])
            return ComicService._get_image_from_archive(archive_path, page_number)
        else:
            chapter_path = os.path.join(comic['path'], chapter['filename'])
            return ComicService._get_image_from_directory(chapter_path, page_number)

    @staticmethod
    def _get_image_from_archive(archive_path, page_number):
        """
        Recupera un'immagine da un archivio zip o rar.

        :param archive_path: Percorso dell'archivio
        :param page_number: Numero della pagina da recuperare
        :return: Tuple contenente i dati dell'immagine e il mimetype
        """
        if archive_path.lower().endswith(('.cbz', '.zip')):
            with zipfile.ZipFile(archive_path, 'r') as archive:
                image_files = [f for f in archive.namelist() if f.lower().endswith(('jpg', 'jpeg', 'png', 'gif'))]
                if 0 <= page_number < len(image_files):
                    image_filename = image_files[page_number]
                    image_data = archive.read(image_filename)
                    mimetype = ComicService._get_mimetype(image_filename)
                    return image_data, mimetype
                else:
                    raise FileNotFoundError("Pagina non trovata")
        
        elif archive_path.lower().endswith(('.cbr', '.rar')):
            with rarfile.RarFile(archive_path, 'r') as archive:
                image_files = [f for f in archive.namelist() if f.lower().endswith(('jpg', 'jpeg', 'png', 'gif'))]
                if 0 <= page_number < len(image_files):
                    image_filename = image_files[page_number]
                    image_data = archive.read(image_filename)
                    mimetype = ComicService._get_mimetype(image_filename)
                    return image_data, mimetype
                else:
                    raise FileNotFoundError("Pagina non trovata")

    @staticmethod
    def _get_image_from_directory(chapter_path, page_number):
        """
        Recupera un'immagine da una directory di immagini.

        :param chapter_path: Percorso della directory del capitolo
        :param page_number: Numero della pagina da recuperare
        :return: Tuple contenente i dati dell'immagine e il mimetype
        """
        valid_extensions = ('.jpg', '.jpeg', '.png', '.gif')
        image_files = [f for f in os.listdir(chapter_path) if f.lower().endswith(valid_extensions)]
        image_files.sort()  # Ordina i file per assicurare l'ordine corretto

        if 0 <= page_number < len(image_files):
            image_filename = image_files[page_number]
            image_path = os.path.join(chapter_path, image_filename)
            
            # Leggi i dati dell'immagine
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                mimetype = ComicService._get_mimetype(image_filename)
                return image_data, mimetype
        else:
            raise FileNotFoundError("Pagina non trovata")

    @staticmethod
    def _get_mimetype(filename):
        """
        Determina il mimetype dell'immagine basato sull'estensione del file.

        :param filename: Nome del file dell'immagine
        :return: Stringa del mimetype
        """
        if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
            return 'image/jpeg'
        elif filename.lower().endswith('.png'):
            return 'image/png'
        elif filename.lower().endswith('.gif'):
            return 'image/gif'
        else:
            return 'application/octet-stream'
