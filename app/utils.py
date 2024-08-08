import os
import zipfile
import rarfile
import io
from PIL import Image
from flask import current_app

def allowed_file(filename, allowed_extensions=None):
    """
    Verifica se un file ha un'estensione consentita.

    :param filename: Nome del file
    :param allowed_extensions: Set di estensioni consentite (opzionale)
    :return: True se il file è consentito, altrimenti False
    """
    if allowed_extensions is None:
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'zip', 'cbz'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_images_from_zip(zip_path):
    """
    Estrae le immagini da un file ZIP in memoria.

    :param zip_path: Percorso al file ZIP
    :return: Lista di oggetti Image di PIL
    """
    images = []
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file in zip_ref.namelist():
            if allowed_file(file, {'jpg', 'jpeg', 'png', 'gif'}):
                with zip_ref.open(file) as image_file:
                    image = Image.open(io.BytesIO(image_file.read()))
                    images.append(image)
    return images

def get_comic_page_path(comic_id, chapter_number, page_number):
    """
    Genera un percorso relativo per una pagina specifica di un fumetto.

    :param comic_id: ID del fumetto
    :param chapter_number: Numero del capitolo
    :param page_number: Numero della pagina
    :return: Percorso relativo alla pagina
    """
    return os.path.join('comics', str(comic_id), str(chapter_number), f'{page_number}.jpg')

def save_image(image, path):
    """
    Salva un oggetto Image di PIL in un percorso specificato.

    :param image: Oggetto Image di PIL
    :param path: Percorso dove salvare l'immagine
    """
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    image.save(path)

def extract_metadata_from_filename(filename):
    """
    Estrae i metadati dal nome del file, come il titolo e l'autore.

    :param filename: Nome del file
    :return: Dizionario con i metadati estratti
    """
    base = os.path.basename(filename)
    name, ext = os.path.splitext(base)
    parts = name.split('_')
    return {
        'title': parts[0] if len(parts) > 0 else 'Unknown',
        'author': parts[1] if len(parts) > 1 else 'Unknown'
    }

def read_image_from_archive(archive_path, image_filename):
    """
    Legge un'immagine da un archivio compresso in memoria.

    :param archive_path: Percorso al file dell'archivio (.zip o .cbz)
    :param image_filename: Nome del file dell'immagine all'interno dell'archivio
    :return: Oggetto Image di PIL, o None se l'immagine non è trovata
    """
    try:
        with zipfile.ZipFile(archive_path, 'r') as archive:
            # Verifica se il file esiste nell'archivio
            if image_filename in archive.namelist():
                # Leggi il file in memoria
                with archive.open(image_filename) as image_file:
                    image_data = image_file.read()
                    image = Image.open(io.BytesIO(image_data))
                    return image
            else:
                print(f"File '{image_filename}' non trovato nell'archivio '{archive_path}'.")
                return None
    except zipfile.BadZipFile:
        print(f"Errore: Il file '{archive_path}' non è un archivio valido.")
        return None
    except Exception as e:
        print(f"Errore sconosciuto durante la lettura dell'immagine: {e}")
        return None

def list_images(path, is_archive):
    """
    Restituisce una lista di file immagine in una directory o in un archivio.

    :param path: Percorso della directory o dell'archivio
    :param is_archive: Booleano che indica se il percorso è un archivio (ZIP/RAR)
    :return: Lista di file immagine con estensioni valide
    """
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif')
    images = []

    if is_archive:
        if path.lower().endswith(('.cbz', '.zip')):
            # Gestione di archivi ZIP
            with zipfile.ZipFile(path, 'r') as archive:
                for file_info in archive.infolist():
                    if file_info.filename.lower().endswith(valid_extensions):
                        images.append(file_info.filename)
        elif path.lower().endswith(('.cbr', '.rar')):
            # Gestione di archivi RAR
            with rarfile.RarFile(path, 'r') as archive:
                for file_info in archive.infolist():
                    if file_info.filename.lower().endswith(valid_extensions):
                        images.append(file_info.filename)
    else:
        # Gestione di directory locali
        for file in os.listdir(path):
            if file.lower().endswith(valid_extensions):
                images.append(file)

    return images