import os
from flask import Flask
from .extensions import db, migrate, scheduler
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

logger = logging.getLogger(__name__)


def create_app(config='config.TestingConfig'):
    app = Flask(__name__)
    app.config.from_object(config)
    print(f'created app with config: {config}')
    db.init_app(app)
    migrate.init_app(app, db)
    scheduler.init_app(app)

    def is_debug_mode():
        """Get app debug status."""
        debug = os.environ.get("FLASK_DEBUG")
        if not debug:
            return app.debug
        return debug.lower() not in ("0", "false", "no")

    def is_werkzeug_reloader_process():
        """Get werkzeug status."""
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    with app.app_context():
        if is_debug_mode() and not is_werkzeug_reloader_process():
            pass
        else:
            if app.config.get('SCHEDULER_ENABLE', False):
                # scheduler.remove_all_jobs()
                print('SCHEDULER START')
                from . import tasks  # noqa: F401
                scheduler.start()
                print()

        from . import companies
        app.register_blueprint(companies.bp)
        app.add_url_rule('/', endpoint='index')

        from . import gtfs_routes
        app.register_blueprint(gtfs_routes.bp)

        from . import api
        app.register_blueprint(api.bp)

        return app
