from io import BytesIO
import os
from flask import render_template, redirect, send_file, url_for, abort
from app import app, mongo
from app.models import Comic, Chapter
from app.repositories.mongo.chapter import ChapterRepository
from app.repositories.mongo.comic import ComicRepository
from app.services import ComicScanner, OptimizedComicScanner, ComicService
from PIL import Image

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
            cover = comic.get('cover', None)
            if cover:
                if cover.startswith('http://') or cover.startswith('https://'):
                    comic['cover'] = cover
                else:
                    comic['cover'] = url_for('static', filename='images/comic.jpg')
            else:
                comic['cover'] = url_for('static', filename='images/comic.jpg')


        return render_template('home.html', comics=comics)
    
    @app.route('/comic/<comic_slug>')
    @app.route('/comic/<comic_slug>/<int:page_number>')
    def view_comic(comic_slug, page_number=1):
        """
        Visualizza i dettagli di un fumetto, inclusi i capitoli.
        """
        comic_repo = ComicRepository(mongo)
        comic = comic_repo.get_by_slug(comic_slug)
        chapters_per_page = app.config['CHAPTERS_PER_PAGE']
        offset = (page_number - 1) * chapters_per_page
        
        # Recupera solo i capitoli necessari per la pagina corrente
        chapters = comic['chapters'][offset:offset + chapters_per_page]
        
        # Calcola il numero totale di pagine
        total_chapters = len(comic['chapters'])
        total_pages = (total_chapters + chapters_per_page - 1) // chapters_per_page
        
        return render_template('comic.html', comic=comic, chapters=chapters, page_number=page_number, total_pages=total_pages)

    @app.route('/comic/<comic_slug>/chapter/<chapter_number>', methods=['GET'])
    def view_chapter(comic_slug, chapter_number):
        """
        Visualizza le immagini di un capitolo specifico del fumetto.

        :param comic_slug: slug del fumetto
        :param chapter_number: numero del capitolo
        :return: Renderizza la pagina del capitolo o restituisce un errore
        """
        # Recupera il fumetto dal database
        comic_repo = ComicRepository(mongo)
        chapter_repo = ChapterRepository(mongo)
        comic = comic_repo.get_by_slug(comic_slug)

        chapter_number = float(chapter_number.replace('-', '.'))

        # Recupera il capitolo dal database
        chapter = chapter_repo.get_by_number(comic_slug, chapter_number)
        if chapter is None:
            abort(404, description="Capitolo non trovato.")

        images = chapter['page_count']
        chapter_index = comic['chapters'].index(chapter)
        page = chapter_index // app.config['CHAPTERS_PER_PAGE'] + 1

        chapters = comic['chapters']

        prev_ch = chapters[chapters.index(chapter) - 1]["number"] if chapters.index(chapter) > 0 else None
        next_ch = chapters[chapters.index(chapter) + 1]["number"] if chapters.index(chapter) < len(chapters) - 1 else None
        prev_ch = str(prev_ch).replace('.', '-') if prev_ch is not None else None
        next_ch = str(next_ch).replace('.', '-') if next_ch is not None else None

        return render_template('chapter.html', comic=comic, chapter=chapter, images=images, page=page, prev=prev_ch, next=next_ch)

    @app.route('/comic/<comic_slug>/chapter/<chapter_number>/<int:page_number>')
    def view_page(comic_slug, chapter_number, page_number):
        """
        Visualizza una pagina specifica di un capitolo di un fumetto.
        """
        print(f"Requesting page {page_number} of chapter {chapter_number} for comic {comic_slug}")
        try:
            chapter_number = float(chapter_number.replace('-', '.'))
            result = ComicService.get_page_image(comic_slug, chapter_number, page_number)
            if result is None:
                abort(404, description="Pagina non trovata")
            image_data, mimetype = result
            return send_file(BytesIO(image_data), mimetype=mimetype)
        except FileNotFoundError:
            abort(404, description="Pagina non trovata")
        except Exception as e:
            abort(500, description=str(e))

    @app.route('/comic/<comic_slug>/cover')
    def view_comic_cover(comic_slug):
        """
        Visualizza la copertina di un fumetto.
        """
        print(f"Requesting cover for comic {comic_slug}")
        try:
            comic_repo = ComicRepository(mongo)
            comic = comic_repo.get_by_slug(comic_slug)
            if not comic:
                abort(404, description="Fumetto non trovato")
            if 'cover' not in comic or not comic['cover']:
                cover_url = url_for('static', filename='images/comic.jpg')
                return redirect(cover_url)
            else:
                cover_url = comic['cover']
                if cover_url.startswith('http://') or cover_url.startswith('https://'):
                    return redirect(cover_url)
                else:
                    cover_url = os.path.join(comic['path'], cover_url)
                    print(f"Cover URL is not a valid external link: {cover_url}")
                    #raise FileNotFoundError(f"Cover URL is not a valid external link: {cover_url}")
                    return send_file(cover_url, mimetype='image/jpeg')
        except Exception as e:
            abort(500, description=str(e))

    @app.route('/comic/<comic_slug>/<chapter_number>/cover')
    def view_cover(comic_slug, chapter_number):
        """
        Visualizza una pagina specifica di un capitolo di un fumetto con qualità ridotta.
        """
        print(f"Requesting cover for comic {comic_slug}, chapter {chapter_number}")
        try:
            chapter_number = float(chapter_number.replace('-', '.'))
            # Ottieni i dati dell'immagine e il tipo MIME dal servizio
            result = ComicService.get_page_image(comic_slug, chapter_number, 0)
            if result is None:
                abort(404, description="Pagina non trovata")
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
            abort(404, description="Pagina non trovata")
        except Exception as e:
            abort(500, description=str(e))

        
    @app.route('/scan')
    def scan_comics():
        directory_to_scan = app.config['COMICS_FOLDER'] 
        scanner = OptimizedComicScanner(directory_to_scan, mongo)
        scanner.scan_and_register_comics()
        return redirect(url_for('index'))


