import os
import zipfile
import rarfile
import io
from PIL import Image
from flask import current_app
import json
from slugify import slugify

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

def list_images(path, is_archive=False):
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

# app/utils.py
def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def generate_slug(title, language=None, version=None):
    base = f"{title}-{language}" if language else title
    if version:
        base += f"-{version}"
    slug = slugify(base)
    return slug

def calculate_comic_hash(comic_path):
    """
    Calcola hash per un fumetto basato su metadati e struttura dei file.
    Include tutti i metadata.json (fumetto e capitoli) nel calcolo dell'hash.
    
    :param comic_path: Percorso alla directory del fumetto
    :return: Hash MD5 hex del contenuto del fumetto
    """
    import hashlib
    
    hash_md5 = hashlib.md5()
    
    # Hash della struttura completa (inclusi TUTTI i metadata.json)
    items = []
    metadata_files = []
    
    for root, dirs, files in os.walk(comic_path):
        for file in sorted(files):  # Ordine consistente
            file_path = os.path.join(root, file)
            try:
                rel_path = os.path.relpath(file_path, comic_path)
                stat = os.stat(file_path)
                
                if file == "metadata.json":
                    # I metadata.json sono critici: leggi il contenuto completo
                    with open(file_path, 'rb') as f:
                        metadata_content = f.read()
                    metadata_files.append(f"{rel_path}:{len(metadata_content)}:{stat.st_mtime}:{metadata_content.hex()}")
                else:
                    # Per altri file usa nome + dimensione + timestamp
                    file_info = f"{rel_path}:{stat.st_size}:{stat.st_mtime}"
                    items.append(file_info)
            except (OSError, ValueError):
                # Ignora file non accessibili
                continue
    
    # Aggiungi prima tutti i metadata.json (ordinati per path)
    for metadata in sorted(metadata_files):
        hash_md5.update(metadata.encode('utf-8'))
    
    # Poi aggiungi tutti gli altri file ordinati
    for item in sorted(items):
        hash_md5.update(item.encode('utf-8'))
    
    return hash_md5.hexdigest()

def calculate_chapter_hash(chapter_path, is_archive=False):
    """
    Calcola hash per un singolo capitolo.
    
    :param chapter_path: Percorso al capitolo (file archivio o directory)
    :param is_archive: True se è un file archivio, False se è una directory
    :return: Hash MD5 hex del contenuto del capitolo
    """
    import hashlib
    
    hash_md5 = hashlib.md5()
    
    if is_archive:
        # Per archivi: hash del file stesso
        try:
            with open(chapter_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except (OSError, IOError):
            # Se non riusciamo a leggere il file, usa solo il nome e la dimensione
            try:
                stat = os.stat(chapter_path)
                file_info = f"{os.path.basename(chapter_path)}:{stat.st_size}:{stat.st_mtime}"
                hash_md5.update(file_info.encode('utf-8'))
            except OSError:
                # Fallback: usa solo il nome del file
                hash_md5.update(os.path.basename(chapter_path).encode('utf-8'))
    else:
        # Per directory: hash di tutti i file immagine
        try:
            images = list_images(chapter_path, is_archive=False)
            items = []
            for img_name in sorted(images):
                try:
                    img_path = os.path.join(chapter_path, img_name)
                    stat = os.stat(img_path)
                    file_info = f"{img_name}:{stat.st_size}:{stat.st_mtime}"
                    items.append(file_info)
                except OSError:
                    continue
            
            # Aggiungi tutti gli item ordinati
            for item in sorted(items):
                hash_md5.update(item.encode('utf-8'))
            
            # Hash dei metadati del capitolo se presenti
            metadata_path = os.path.join(chapter_path, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    hash_md5.update(f.read())
                    
        except Exception as e:
            # Fallback: usa solo il nome della directory
            hash_md5.update(os.path.basename(chapter_path).encode('utf-8'))
    
    return hash_md5.hexdigest()