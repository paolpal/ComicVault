# __init__.py
import logging
import sys
from flask import Flask
from flask_pymongo import PyMongo

# Configurazione logging per inviare output a stdout (visibile con docker logs)
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

app = Flask(__name__)
app.config.from_object('config')

mongo = PyMongo(app)

from app import views
from app import controllers

