# __init__.py
from flask import Flask
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config.from_object('config')

mongo = PyMongo(app)

from app import views
from app import controllers

