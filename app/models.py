from app import mongo
from bson.objectid import ObjectId
import os
import zipfile
import rarfile

class Comic:
    def __init__(self, title, path, chapters=None):
        self.title = title
        self.chapters = chapters or []
        self.path = path

    def save(self):
        """
        Salva il fumetto nel database.
        """
        comic_data = {
            'title': self.title,
            'chapters': self.chapters,
            'path': self.path
        }
        result = mongo.db.comics.insert_one(comic_data)
        return result.inserted_id

    @staticmethod
    def get_by_id(comic_id):
        """
        Recupera un fumetto dal database dato il suo ID.
        """
        comic = mongo.db.comics.find_one_or_404({'_id': ObjectId(comic_id)})
    
        # Ordinamento dei capitoli per numero
        comic['chapters'] = sorted(comic['chapters'], key=lambda x: x['number'])
        return comic

    @staticmethod
    def list_all():
        """
        Restituisce una lista di tutti i fumetti nel database.
        """
        return mongo.db.comics.find()

class Chapter:
    def __init__(self, comic_id, title, number, filename, page_count, is_archive):
        self.comic_id = comic_id
        self.title = title
        self.number = number
        self.filename = filename  # Percorso dell'archivio o della directory
        self.page_count = page_count
        self.is_archive = is_archive  # Indica se il percorso è un archivio

    def save(self):
        """
        Salva il capitolo nel database.
        """
        chapter_data = {
            'title': self.title,
            'number': self.number,
            'filename': self.filename,
            'page_count': self.page_count,
            'is_archive': self.is_archive
        }
        result = mongo.db.comics.update_one(
            {'_id': ObjectId(self.comic_id)},
            {'$push': {'chapters': chapter_data}}
        )
        return result.modified_count
    
    @staticmethod
    def find_by_number(comic_id, number):
        """
        Trova un capitolo specifico basato sul numero del capitolo per un fumetto specifico.

        :param comic_id: ID del fumetto
        :param number: Numero del capitolo da cercare
        :return: Capitolo se trovato, altrimenti None
        """
        # Query MongoDB per trovare il capitolo specifico nel fumetto
        comic = mongo.db.comics.find_one(
            {'_id': ObjectId(comic_id), 'chapters.number': number},
            {'chapters.$': 1}
        )
        
        if comic and 'chapters' in comic:
            return comic['chapters'][0]
        return None