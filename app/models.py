class Comic:
    def __init__(self, title, original_title, author, plot, year, genres, status, language, cover, tags, path, chapters=None):
        self.title = title
        self.original_title = original_title
        self.author = author
        self.plot = plot
        self.year = year
        self.genres = genres
        self.status = status
        self.language = language
        self.cover = cover
        self.tags = tags
        self.path = path
        self.chapters = chapters or []

    def __str__(self) -> str:
        return f"Comic(title={self.title}, author={self.author}, year={self.year}, path={self.path})"

class Chapter:
    def __init__(self, comic_id, title, number, filename, page_count, is_archive, language, publication_date, rtl):
        self.comic_id = comic_id
        self.title = title
        self.number = number
        self.filename = filename  # Percorso dell'archivio o della directory
        self.page_count = page_count
        self.is_archive = is_archive  # Indica se il percorso è un archivio
        self.language = language
        self.publication_date = publication_date
        self.rtl = rtl

    def __str__(self) -> str:
        return f"Chapter(title={self.title}, number={self.number}, comic_id={self.comic_id}, pages={self.page_count}, rtl={self.rtl}, filename={self.filename})"