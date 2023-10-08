import os
from flask import Flask
from .extensions import db, migrate, scheduler


def create_app(config='config.ProductionConfig'):
    app = Flask(__name__)
    app.config.from_object(config)
    print(f'created app with config: {config}')
    db.init_app(app)
    migrate.init_app(app, db)
    scheduler.init_app(app)

    def is_debug_mode():
        """Get app debug status."""
        debug = app.config.get("FLASK_DEBUG", False)
        return debug is True or app.debug

    def is_werkzeug_reloader_process():
        """Get werkzeug status."""
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    with app.app_context():
        # pylint: disable=W0611
        if is_debug_mode() and not is_werkzeug_reloader_process():
            pass
        else:
            # scheduler.remove_all_jobs()
            print('Scheduler Start')
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
