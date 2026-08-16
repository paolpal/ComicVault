from io import BytesIO
import os
import threading
from flask import render_template, redirect, send_file, url_for, abort, flash, request
from app import app, mongo
from app.models import Comic, Chapter
from app.repositories.mongo.chapter import ChapterRepository
from app.repositories.mongo.comic import ComicRepository
from app.services import ComicScanner, OptimizedComicScanner, ComicService
from app.utils import convert_webp
from PIL import Image
import logging
import requests

logger = logging.getLogger(__name__)

class ComicController:
    @staticmethod
    @app.route('/')
    @app.route('/home')
    def index():
        """
        Visualizza la lista dei fumetti.
        """
        comic_repo = ComicRepository(mongo)
        comics = comic_repo.list_all()

        comics = list(comics)  # Converti il cursore in una lista

        for comic in comics:
            cover = comic.cover
            if cover:
                if cover.startswith('http://') or cover.startswith('https://'):
                    comic['cover'] = cover
                else:
                    comic['cover'] = url_for('static', filename='images/comic.jpg')
            else:
                comic['cover'] = url_for('static', filename='images/comic.jpg')


        return render_template('home.html', comics=comics)
    
    @app.route('/continue-reading')
    def continue_reading():
        """
        Visualizza la pagina "Continua a leggere" (basata su LocalStorage).
        """
        return render_template('continue_reading.html')
    
    @app.route('/comic/<string:comic_slug>')
    @app.route('/comic/<string:comic_slug>/<int:page_number>')
    def view_comic(comic_slug, page_number=1):
        """
        Visualizza i dettagli di un fumetto, inclusi i capitoli.
        """
        comic_repo = ComicRepository(mongo)
        comic_slug = str(comic_slug)
        comic = comic_repo.get_by_slug(comic_slug)

        if comic is None:
            abort(404, description="Comic not found.")

        chapters_per_page = app.config['CHAPTERS_PER_PAGE']
        offset = (page_number - 1) * chapters_per_page
        
        # Recupera solo i capitoli necessari per la pagina corrente
        chapters = comic['chapters'][offset:offset + chapters_per_page]
        
        # Calcola il numero totale di pagine
        total_chapters = len(comic['chapters'])
        total_pages = (total_chapters + chapters_per_page - 1) // chapters_per_page
        
        return render_template('comic.html', comic=comic, chapters=chapters, page_number=page_number, total_pages=total_pages)

    @app.route('/comic/<string:comic_slug>/chapter/<float:chapter_seq_number>', methods=['GET'])
    def view_chapter(comic_slug, chapter_seq_number):
        """
        Visualizza le immagini di un capitolo specifico del fumetto.

        :param comic_slug: slug del fumetto
        :param chapter_number: numero del capitolo
        :return: Renderizza la pagina del capitolo o restituisce un errore
        """

        comic_slug = str(comic_slug)
        chapter_seq_number = float(chapter_seq_number)

        # Recupera il fumetto dal database
        comic_repo = ComicRepository(mongo)
        chapter_repo = ChapterRepository(mongo)
        comic = comic_repo.get_by_slug(comic_slug)

        if comic is None:
            abort(404, description="Comic not found.")        

        logger.info(f"Requesting chapter {chapter_seq_number} for comic {comic_slug}")

        # Recupera il capitolo dal database
        chapter = chapter_repo.get_by_number(comic_slug, chapter_seq_number)
        if chapter is None:
            abort(404, description="Chapter not found.")

        logger.info(f"Chapter retrieved: {chapter.__dict__}")

        images = chapter['page_count']
        chapter_index = comic['chapters'].index(chapter)
        page = chapter_index // app.config['CHAPTERS_PER_PAGE'] + 1

        chapters:list[Chapter] = comic['chapters']

        prev_ch = chapters[chapters.index(chapter) - 1]["seq_number"] if chapters.index(chapter) > 0 else None
        next_ch = chapters[chapters.index(chapter) + 1]["seq_number"] if chapters.index(chapter) < len(chapters) - 1 else None

        return render_template('chapter.html', comic=comic, chapter=chapter, images=images, page=page, prev=prev_ch, next=next_ch)

    @app.route('/comic/<string:comic_slug>/chapter/<float:chapter_seq_number>/<int:page_number>')
    def view_page(comic_slug, chapter_seq_number, page_number):
        """
        Visualizza una pagina specifica di un capitolo di un fumetto.
        """
        print(f"Requesting page {page_number} of chapter {chapter_seq_number} for comic {comic_slug}")
        try:
            comic_slug = str(comic_slug)
            chapter_seq_number = float(chapter_seq_number)
            page_number = int(page_number)
            result = ComicService.get_page_image(comic_slug, chapter_seq_number, page_number)
            if result is None:
                abort(404, description="Page not found.")
            image_data, mimetype = result
            
            resolution = request.cookies.get('image_resolution', 'high')
            if resolution in ['low', 'medium']:
                try:
                    image = Image.open(BytesIO(image_data))
                    max_size = 800 if resolution == 'low' else 1200
                    image.thumbnail((max_size, max_size))
                    buffer = BytesIO()
                    fmt = image.format if image.format else ('PNG' if mimetype == 'image/png' else 'JPEG')
                    image.save(buffer, format=fmt)
                    buffer.seek(0)
                    return send_file(buffer, mimetype=mimetype)
                except Exception as e:
                    logger.error(f"Error resizing image: {e}")
                    return send_file(BytesIO(image_data), mimetype=mimetype)
                    
            return send_file(BytesIO(image_data), mimetype=mimetype)
        except FileNotFoundError:
            abort(404, description="Page not found.")
        except Exception as e:
            abort(500, description=str(e))

    @app.route('/comic/<string:comic_slug>/cover')
    def view_comic_cover(comic_slug):
        """
        Visualizza la copertina di un fumetto.
        """
        try:
            comic_slug = str(comic_slug)
            logger.info(f"Requesting cover for comic {comic_slug}")
            comic_repo = ComicRepository(mongo)
            comic = comic_repo.get_by_slug(comic_slug)
            logger.info(f"Comic retrieved: {comic}")
            if not comic:
                logger.error(f"Comic with slug {comic_slug} not found.")
                abort(404, description="Comic not found.")
            if 'cover' not in comic.__dict__ or not comic['cover']:
                cover_url = url_for('static', filename='images/comic.jpg')
                return redirect(cover_url)
            else:
                cover_url = comic['cover']
                logger.info(f"Cover URL: {cover_url}")
                
                # Gestione cover remote
                if cover_url.startswith('http://') or cover_url.startswith('https://'):
                    logger.info(f"Fetching remote cover: {cover_url}")
                    response = requests.get(cover_url, timeout=10)
                    response.raise_for_status()
                    
                    image_data = response.content
                    content_type = response.headers.get('Content-Type', '')
                    
                    # Controlla se è WebP
                    if 'webp' in content_type.lower() or cover_url.lower().endswith('.webp'):
                        logger.info("Converting WebP to JPG/PNG")
                        converted_data, ext = convert_webp(image_data)
                        mimetype = 'image/png' if ext == '.png' else 'image/jpeg'
                        return send_file(BytesIO(converted_data), mimetype=mimetype)
                    else:
                        # Restituisci l'immagine così com'è
                        mimetype = content_type if content_type.startswith('image/') else 'image/jpeg'
                        return send_file(BytesIO(image_data), mimetype=mimetype)
                else:
                    # Cover locale
                    cover_path = os.path.join(comic['path'], cover_url)
                    logger.info(f"Serving local cover: {cover_path}")
                    
                    # Controlla se è WebP locale
                    if cover_path.lower().endswith('.webp'):
                        with open(cover_path, 'rb') as f:
                            webp_data = f.read()
                        converted_data, ext = convert_webp(webp_data)
                        mimetype = 'image/png' if ext == '.png' else 'image/jpeg'
                        return send_file(BytesIO(converted_data), mimetype=mimetype)
                    else:
                        return send_file(cover_path, mimetype='image/jpeg')
                        
        except requests.RequestException as e:
            logger.error(f"Error fetching remote cover for comic {comic_slug}: {e}")
            # Fallback a immagine di default
            cover_url = url_for('static', filename='images/comic.jpg')
            return redirect(cover_url)
        except Exception as e:
            logger.error(f"Error while retrieving cover for comic {comic_slug}: {e}")
            abort(500, description=str(e))

    @app.route('/comic/<string:comic_slug>/<float:chapter_seq_number>/cover')
    def view_cover(comic_slug, chapter_seq_number):
        """
        Visualizza una pagina specifica di un capitolo di un fumetto con qualità ridotta.
        """
        print(f"Requesting cover for comic {comic_slug}, chapter {chapter_seq_number}")
        try:
            chapter_seq_number = float(chapter_seq_number)
            comic_slug = str(comic_slug)
            # Ottieni i dati dell'immagine e il tipo MIME dal servizio
            result = ComicService.get_page_image(comic_slug, chapter_seq_number, 0)
            if result is None:
                abort(404, description="Page not found.")
            image_data, mimetype = result
            
            # Apri l'immagine utilizzando Pillow
            image = Image.open(BytesIO(image_data))
            
            # Salva l'immagine in un buffer con qualità ridotta
            buffer = BytesIO()
            image.save(buffer, format=image.format, quality=1)  # Modifica 'quality' secondo le tue esigenze
            buffer.seek(0)
            
            # Restituisci l'immagine con qualità ridotta
            return send_file(buffer, mimetype=mimetype)
        
        except FileNotFoundError:
            abort(404, description="Page not found.")
        except Exception as e:
            abort(500, description=str(e))

        
    @app.route('/scan')
    def scan_comics():
        """
        Avvia la scansione dei fumetti in background.
        Restituisce immediatamente una risposta per evitare timeout.
        """
        directory_to_scan = app.config['COMICS_FOLDER']
        
        def scan_in_background():
            """Funzione eseguita in background per la scansione."""
            try:
                logger.info("Starting background comic scan...")
                scanner = OptimizedComicScanner(directory_to_scan, mongo)
                scanner.scan_and_register_comics()
                logger.info("Background comic scan completed successfully")
            except Exception as e:
                logger.error(f"Error during background scan: {e}", exc_info=True)
        
        # Avvia la scansione in un thread separato
        scan_thread = threading.Thread(target=scan_in_background, daemon=True)
        scan_thread.start()
        
        logger.info("Scan started in background")
        return redirect(url_for('index'))


