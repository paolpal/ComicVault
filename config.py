# config.py
import os
#MONGO_URI = "mongodb://comic-vault-db:27017/comic_vault"
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://192.168.1.10:27017/comic_vault')
CHAPTERS_PER_PAGE = 20
COMICS_FOLDER = "/data/comics"
