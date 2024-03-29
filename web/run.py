from flaskr import create_app
import config

if __name__ == "__main__":
    # app = create_app(config=config.TestingConfig)  # Dockerfile should use python run.py
    app = create_app(config=config.DebugConfig)  # Dockerfile should use python run.py
    app.run(host='0.0.0.0', port=5000)
else:
    gunicorn_app = create_app(config.ProductionConfig)
