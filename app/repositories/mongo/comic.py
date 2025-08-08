from bson import ObjectId


class ComicRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def save(self, comic):
        """
        Salva un fumetto nel database.
        """
        comic_data = {
            'title': comic.title,
            'chapters': comic.chapters,
            'path': comic.path,
            'original_title': comic.original_title,
            'author': comic.author,
            'plot': comic.plot,
            'year': comic.year,
            'genres': comic.genres,
            'status': comic.status,
            'language': comic.language,
            'cover': comic.cover,
            'tags': comic.tags
        }
        result = self.mongo.db["comics"].insert_one(comic_data)
        return result.inserted_id

    def get_by_id(self, comic_id):
        """
        Recupera un fumetto dal database dato il suo ID.
        """
        comic = self.mongo.db["comics"].find_one_or_404({'_id': ObjectId(comic_id)})

        # Ordinamento dei capitoli per numero
        comic['chapters'] = sorted(comic['chapters'], key=lambda x: x['number'])
        return comic

    def get_by_title(self, title):
        """
        Recupera un fumetto dal database dato il suo titolo.
        """
        comic = self.mongo.db["comics"].find_one({'title': title})
        if comic:
            # Ordinamento dei capitoli per numero
            comic['chapters'] = sorted(comic['chapters'], key=lambda x: x['number'])
        return comic

    def list_all(self):
        """
        Restituisce una lista di tutti i fumetti nel database.
        """
        return self.mongo.db["comics"].find()

    def drop(self):
        """
        Elimina tutti i fumetti dal database.
        """
        self.mongo.db["comics"].drop()
        return True