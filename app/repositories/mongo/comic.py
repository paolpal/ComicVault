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
            'slug': comic.slug,
            'version': comic.version,
            'tags': comic.tags,
            'content_hash': comic.content_hash
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

    def get_by_slug(self, slug):
        """
        Recupera un fumetto dal database dato il suo slug.
        """
        comic = self.mongo.db["comics"].find_one({'slug': slug})
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

    def get_by_path(self, path):
        """
        Recupera un fumetto dal database dato il suo percorso.
        """
        return self.mongo.db["comics"].find_one({'path': path})

    def update_hash(self, comic_id, new_hash):
        """
        Aggiorna solo l'hash di un fumetto esistente.
        """
        result = self.mongo.db["comics"].update_one(
            {'_id': ObjectId(comic_id)},
            {'$set': {'content_hash': new_hash}}
        )
        return result.modified_count > 0

    def delete(self, comic_id):
        """
        Elimina un fumetto dal database dato il suo ID.
        """
        result = self.mongo.db["comics"].delete_one({'_id': ObjectId(comic_id)})
        return result.deleted_count > 0