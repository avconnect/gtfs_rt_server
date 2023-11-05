from flaskr.models import *
from flaskr import create_app
from config import TestingConfig

app = create_app(TestingConfig)
with app.app_context():
    db.create_all()
