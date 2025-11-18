from typing import Optional
from bson import ObjectId
import json

from app.models import Chapter
import logging

logger = logging.getLogger(__name__)

class ChapterRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def save(self, chapter) -> bool:
        """
        Salva un capitolo nel database.
        """
        chapter_data = chapter.__dict__
        logger.info(f"Saving chapter: {chapter_data}")
        result = self.mongo.db["comics"].update_one(
            {'_id': ObjectId(chapter.comic_id)},
            {'$push': {'chapters': chapter_data}}
        )
        return result.modified_count > 0

    def get_by_number(self, comic_slug:str, seq_number:int) -> Optional[Chapter]:
        """
        Trova un capitolo specifico basato sul numero del capitolo per un fumetto specifico.

        :param comic_id: ID del fumetto
        :param number: Numero del capitolo da cercare
        :return: Capitolo se trovato, altrimenti None
        """
        # Query MongoDB per trovare il capitolo specifico nel fumetto
        comic = self.mongo.db["comics"].find_one(
            {'slug': comic_slug, 'chapters.seq_number': seq_number},
            {'chapters.$': 1}
        )

        if comic and 'chapters' in comic:
            logger.info(f"Found chapter {seq_number} for comic {comic_slug}")
            logger.info(f"Chapter data from DB: {comic['chapters'][0]}")
            chapter = Chapter(**comic['chapters'][0])
            logger.info(f"Chapter data: {chapter}")
            return chapter
        return None
    
    def drop(self) -> bool:
        """
        Elimina tutti i capitoli dal database.
        """
        self.mongo.db["chapters"].drop()
        return True

    def delete_by_comic_id(self, comic_id:str) -> bool:
        """
        Rimuove tutti i capitoli di un fumetto specifico.
        """
        result = self.mongo.db["comics"].update_one(
            {'_id': ObjectId(comic_id)},
            {'$set': {'chapters': []}}
        )
        return result.modified_count > 0

    def get_by_comic_and_filename(self, comic_id:str, filename:str) -> Optional[Chapter]:
        """
        Recupera un capitolo specifico basato sul comic_id e filename.
        """
        comic = self.mongo.db["comics"].find_one(
            {'_id': ObjectId(comic_id), 'chapters.filename': filename},
            {'chapters.$': 1}
        )
        
        if comic and 'chapters' in comic:
            return Chapter(**comic['chapters'][0])
        return None