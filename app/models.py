from typing import Optional
from app.utils import generate_slug

class Comic:
    def __init__(self, 
                title:str, 
                original_title:str, 
                author:str, 
                plot:str, 
                year:int, 
                genres:list, 
                status:str, 
                language:str, 
                cover:str, 
                tags:list[str], 
                path:str, 
                version:Optional[str]=None, 
                chapters:Optional[list]=None, 
                content_hash:Optional[str]=None, 
                _id:Optional[str]=None, 
                **kwargs):
        self.id = _id
        self.title = title
        self.original_title = original_title
        self.author = author if author else "Unknown"
        self.plot = plot
        self.year = year if year else "Unknown"
        self.genres = genres
        self.status = status
        self.language = language if language else None
        self.cover = cover
        self.tags = tags
        self.path = path
        self.version = version
        self.slug = generate_slug(title, language, version)
        self.chapters = chapters or []
        self.chapters = [Chapter(**ch) for ch in self.chapters]
        self.content_hash = content_hash

    def __getitem__(self, key):
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self) -> str:
        return f"Comic(title={self.title}, author={self.author}, year={self.year}, path={self.path})"

class Chapter:
    def __init__(self, comic_id, title:str, number:int|str, seq_number:int, filename:str, page_count:int, is_archive:bool, language:Optional[str], publication_date:Optional[str], rtl:bool, content_hash=None):
        self.comic_id = comic_id
        self.title = title
        self.number = number
        self.seq_number = seq_number if seq_number is not None else number
        self.filename = filename  # Percorso dell'archivio o della directory
        self.page_count = page_count
        self.is_archive = is_archive  # Indica se il percorso è un archivio
        self.language = language
        self.publication_date = publication_date
        self.rtl = rtl
        self.content_hash = content_hash

    def __eq__(self, other):
        if not isinstance(other, Chapter):
            return False
        return self.comic_id == other.comic_id and self.seq_number == other.seq_number

    def __getitem__(self, key):
        return getattr(self, key)

    def __str__(self) -> str:
        return f"Chapter(title={self.title}, number={self.number}, comic_id={self.comic_id}, pages={self.page_count}, rtl={self.rtl}, filename={self.filename})"