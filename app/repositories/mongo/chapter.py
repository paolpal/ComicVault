from bson import ObjectId


class ChapterRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def save(self, chapter):
        """
        Salva un capitolo nel database.
        """
        chapter_data = {
            'title': chapter.title,
            'number': chapter.number,
            'filename': chapter.filename,
            'page_count': chapter.page_count,
            'is_archive': chapter.is_archive,
            'language': chapter.language,
            'publication_date': chapter.publication_date,
            'rtl': chapter.rtl,
            'content_hash': chapter.content_hash
        }
        result = self.mongo.db["comics"].update_one(
            {'_id': ObjectId(chapter.comic_id)},
            {'$push': {'chapters': chapter_data}}
        )
        return result.modified_count

    def get_by_number(self, comic_slug, number):
        """
        Trova un capitolo specifico basato sul numero del capitolo per un fumetto specifico.

        :param comic_id: ID del fumetto
        :param number: Numero del capitolo da cercare
        :return: Capitolo se trovato, altrimenti None
        """
        # Query MongoDB per trovare il capitolo specifico nel fumetto
        comic = self.mongo.db["comics"].find_one(
            {'slug': comic_slug, 'chapters.number': number},
            {'chapters.$': 1}
        )

        if comic and 'chapters' in comic:
            return comic['chapters'][0]
        return None
    
    def drop(self):
        """
        Elimina tutti i capitoli dal database.
        """
        self.mongo.db["chapters"].drop()
        return True

    def delete_by_comic_id(self, comic_id):
        """
        Rimuove tutti i capitoli di un fumetto specifico.
        """
        result = self.mongo.db["comics"].update_one(
            {'_id': ObjectId(comic_id)},
            {'$set': {'chapters': []}}
        )
        return result.modified_count > 0

    def get_by_comic_and_filename(self, comic_id, filename):
        """
        Recupera un capitolo specifico basato sul comic_id e filename.
        """
        comic = self.mongo.db["comics"].find_one(
            {'_id': ObjectId(comic_id), 'chapters.filename': filename},
            {'chapters.$': 1}
        )
        
        if comic and 'chapters' in comic:
            return comic['chapters'][0]
        return None