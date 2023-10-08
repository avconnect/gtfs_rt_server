import os
from pytz import utc
from dotenv import load_dotenv

load_dotenv()


class ProductionConfig:
    SECRET_KEY = os.getenv("SECRET_KEY")

    pg_user = os.getenv("POSTGRES_USER")
    pg_pass = os.getenv("POSTGRES_PASSWORD")
    pg_db = os.getenv("POSTGRES_DB")
    pg_host = os.getenv("POSTGRES_HOST")
    pg_port = os.getenv("POSTGRES_PORT")

    SQLALCHEMY_DATABASE_URI = \
        f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ERROR_LOG = os.getenv("ERROR_LOG")
    LOGGING_ENABLED = False
    SCHEDULER_EXECUTORS = {
        "default": {'type': 'threadpool', 'max_workers': 1}
    }


class DebugConfig:
    SECRET_KEY = os.getenv("SECRET_KEY")
    FLASK_DEBUG = True

    pg_user = os.getenv("POSTGRES_USER")
    pg_pass = os.getenv("POSTGRES_PASSWORD")
    pg_db = os.getenv("POSTGRES_DB")
    pg_host = os.getenv("POSTGRES_HOST")
    pg_port = os.getenv("POSTGRES_PORT")

    SQLALCHEMY_DATABASE_URI = \
        f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ERROR_LOG = os.getenv("ERROR_LOG")
    LOGGING_ENABLED = True
    SCHEDULER_EXECUTORS = {
        "default": {'type': 'threadpool', 'max_workers': 1}
    }
