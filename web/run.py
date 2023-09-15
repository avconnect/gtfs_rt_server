from flaskr import create_app
import config
if __name__ == "__main__":
    app = create_app(config=config.ContainerConfig)
    app.run(host='0.0.0.0', port=5000, debug=True)
