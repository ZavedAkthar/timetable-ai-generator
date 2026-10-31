from flask import Flask

from config import Config
from routes.imports import imports_bp
from routes.dashboard import dashboard_bp
from routes.teachers import teachers_bp
from routes.classes import classes_bp
from routes.subjects import subjects_bp
from routes.rooms import rooms_bp
from routes.constraints import constraints_bp
from routes.timetable import timetable_bp


def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Register routes
    blueprints = (
        dashboard_bp,
        teachers_bp,
        classes_bp,
        subjects_bp,
        rooms_bp,
        constraints_bp,
        timetable_bp,
         imports_bp,
    )

    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)