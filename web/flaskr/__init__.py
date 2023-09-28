import os
from flask import Flask
from .extensions import db, migrate, scheduler


def create_app(config='config.ContainerConfig'):
    app = Flask(__name__)
    app.config.from_object(config)
    print(f'created app with config: {config}')
    db.init_app(app)
    migrate.init_app(app, db)
    scheduler.init_app(app)

    with app.app_context():
        # pylint: disable=W0611
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            #scheduler.remove_all_jobs()
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
