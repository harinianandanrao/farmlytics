import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "farmlytics-secret-key-2024")

    # Render (and similar PaaS) has an ephemeral filesystem — use /tmp
    if os.environ.get("RENDER"):
        db_path = "/tmp/farmlytics.db"
        upload_dir = "/tmp/uploads"
    else:
        base = os.path.dirname(os.path.dirname(__file__))
        db_path = os.path.join(base, "instance", "farmlytics.db")
        upload_dir = os.path.join(base, "uploads")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{db_path}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = upload_dir
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

    # Flask-Mail configuration (set MAIL_* env vars in Render dashboard)
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME", "noreply@farmlytics.com")

    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.upload import upload_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()
        _seed_admin()

    return app


def _seed_admin():
    from app.models import User
    if not User.query.filter_by(email="admin@farmlytics.com").first():
        admin = User(
            name="Admin",
            email="admin@farmlytics.com",
            role="admin",
            is_verified=True,
        )
        admin.set_password("Admin@1234")
        db.session.add(admin)
        db.session.commit()
