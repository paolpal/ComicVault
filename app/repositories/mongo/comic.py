from typing import Optional
from bson import ObjectId

from app.models import Comic


class ComicRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def save(self, comic) -> bool:
        """
        Salva un fumetto nel database.
        """
        comic_data = comic.__dict__
        result = self.mongo.db["comics"].insert_one(comic_data)
        return result.inserted_id > 0

    def get_by_id(self, comic_id:str) -> Optional[Comic]:
        """
        Recupera un fumetto dal database dato il suo ID.
        """
        comic = self.mongo.db["comics"].find_one_or_404({'_id': ObjectId(comic_id)})
        if comic:
            comic = Comic(**comic)

            # Ordinamento dei capitoli per numero
            comic['chapters'] = sorted(comic['chapters'], key=lambda x: x['seq_number'])
            return comic
        return None

    def get_by_title(self, title:str) -> Optional[Comic]:
        """
        Recupera un fumetto dal database dato il suo titolo.
        """
        comic = self.mongo.db["comics"].find_one({'title': title})
        if comic:
            comic = Comic(**comic)
            # Ordinamento dei capitoli per numero
            comic['chapters'] = sorted(comic['chapters'], key=lambda x: x['seq_number'])
            return comic
        return None

    def get_by_slug(self, slug:str) -> Optional[Comic]:
        """
        Recupera un fumetto dal database dato il suo slug.
        """
        comic = self.mongo.db["comics"].find_one({'slug': slug})
        if comic:
            comic = Comic(**comic)
            # Ordinamento dei capitoli per numero
            comic['chapters'] = sorted(comic['chapters'], key=lambda x: x['seq_number'])
            return comic
        return None

    def list_all(self) -> list[Comic]:
        """
        Restituisce una lista di tutti i fumetti nel database.
        """
        comics = self.mongo.db["comics"].find()
        return [Comic(**comic) for comic in comics]

    def drop(self) -> bool:
        """
        Elimina tutti i fumetti dal database.
        """
        try:
            self.mongo.db["comics"].drop()
            return True
        except Exception as e:
            return False

    def get_by_path(self, path:str) -> Optional[Comic]:
        """
        Recupera un fumetto dal database dato il suo percorso.
        """
        comic = self.mongo.db["comics"].find_one({'path': path})
        if comic:
            return Comic(**comic)
        return None
    
    def update_hash(self, comic_id:str, new_hash:str) -> bool:
        """
        Aggiorna solo l'hash di un fumetto esistente.
        """
        result = self.mongo.db["comics"].update_one(
            {'_id': ObjectId(comic_id)},
            {'$set': {'content_hash': new_hash}}
        )
        return result.modified_count > 0

    def delete(self, comic_id:str) -> bool:
        """
        Elimina un fumetto dal database dato il suo ID.
        """
        result = self.mongo.db["comics"].delete_one({'_id': ObjectId(comic_id)})
        return result.deleted_count > 0