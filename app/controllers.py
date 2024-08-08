from io import BytesIO
from flask import render_template, redirect, send_file, url_for, abort
from app import app, mongo
from app.models import Comic, Chapter
from app.services import ComicScanner, ComicService
from PIL import Image

class ComicController:
    @staticmethod
    @app.route('/')
    @app.route('/home')
    def index():
        """
        Visualizza la lista dei fumetti.
        """
        comics = Comic.list_all()
        return render_template('home.html', comics=comics)
    
    @app.route('/comic/<comic_id>')
    @app.route('/comic/<comic_id>/<int:page_number>')
    def view_comic(comic_id, page_number=1):
        """
        Visualizza i dettagli di un fumetto, inclusi i capitoli.
        """
        comic = Comic.get_by_id(comic_id)
        chapters_per_page = app.config['CHAPTERS_PER_PAGE']
        offset = (page_number - 1) * chapters_per_page
        
        # Recupera solo i capitoli necessari per la pagina corrente
        chapters = comic['chapters'][offset:offset + chapters_per_page]
        
        # Calcola il numero totale di pagine
        total_chapters = len(comic['chapters'])
        total_pages = (total_chapters + chapters_per_page - 1) // chapters_per_page
        
        return render_template('comic.html', comic=comic, chapters=chapters, page_number=page_number, total_pages=total_pages)

    @app.route('/comic/<comic_id>/chapter/<int:chapter_number>', methods=['GET'])
    def view_chapter(comic_id, chapter_number):
        """
        Visualizza le immagini di un capitolo specifico del fumetto.

        :param comic_id: ID del fumetto
        :param chapter_number: numero del capitolo
        :return: Renderizza la pagina del capitolo o restituisce un errore
        """
        # Recupera il fumetto dal database
        comic = Comic.get_by_id(comic_id)
        
        # Recupera il capitolo dal database
        chapter = Chapter.find_by_number(comic_id, chapter_number)
        if chapter is None:
            abort(404, description="Capitolo non trovato.")

        images = chapter['page_count']
        page = chapter_number // app.config['CHAPTERS_PER_PAGE'] + 1

        prev = Chapter.find_by_number(comic_id, chapter_number-1)
        next = Chapter.find_by_number(comic_id, chapter_number+1)

        return render_template('chapter.html', comic=comic, chapter=chapter, images=images, page=page)

    @app.route('/comic/<comic_id>/chapter/<int:chapter_number>/<int:page_number>')
    def view_page(comic_id, chapter_number, page_number):
        """
        Visualizza una pagina specifica di un capitolo di un fumetto.
        """
        try:
            image_data, mimetype = ComicService.get_page_image(comic_id, chapter_number, page_number)
            return send_file(BytesIO(image_data), mimetype=mimetype)
        except FileNotFoundError:
            abort(404, description="Pagina non trovata")
        except Exception as e:
            abort(500, description=str(e))

    @app.route('/comic/<comic_id>/<int:chapter_number>/cover')
    def view_cover(comic_id, chapter_number):
        """
        Visualizza una pagina specifica di un capitolo di un fumetto con qualità ridotta.
        """
        try:
            # Ottieni i dati dell'immagine e il tipo MIME dal servizio
            image_data, mimetype = ComicService.get_page_image(comic_id, chapter_number, 0)
            
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
        scanner = ComicScanner(directory_to_scan, mongo)
        scanner.scan_and_register_comics()
        return redirect(url_for('index'))


