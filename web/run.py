from flaskr import create_app
import config

# app = create_app(config=config.ProductionConfig)  # Dockerfile should use gunicorn
app = create_app(config=config.DebugConfig)  # Dockerfile should use python run.py
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
