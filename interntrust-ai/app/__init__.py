import os
from flask import Flask, render_template

from app.config import config_by_name
from app.extensions import db, migrate, csrf, login_manager, limiter


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)

    # --- extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    from app.models import User, Admin

    @login_manager.user_loader
    def load_user(combined_id):
        # ids are stored as "user:<id>" or "admin:<id>" to keep the two
        # account types cleanly separated within Flask-Login.
        try:
            kind, raw_id = combined_id.split(":", 1)
        except ValueError:
            return None
        if kind == "user":
            return User.query.get(int(raw_id))
        if kind == "admin":
            return Admin.query.get(int(raw_id))
        return None

    # --- blueprints ---
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.student import student_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    # --- CLI commands ---
    from app.cli import register_cli
    register_cli(app)

    # --- error handlers ---
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/500.html"), 500

    # --- template globals ---
    @app.context_processor
    def inject_globals():
        return {"ai_enabled": app.config.get("AI_ENABLED", False)}

    return app
