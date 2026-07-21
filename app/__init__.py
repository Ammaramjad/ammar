import os
from datetime import timedelta

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///student_prediction.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "uploads")
    app.config["MODEL_ARTIFACT_PATH"] = os.path.join(app.instance_path, "model_artifact.pkl")
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    from .routes import auth_bp, main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        _ensure_admin_user()

    return app


def _ensure_admin_user() -> None:
    from .models import User

    admin_username = os.getenv("APP_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("APP_ADMIN_PASSWORD", "admin123")
    existing = User.query.filter_by(username=admin_username).first()
    if existing:
        return

    password_hash = bcrypt.generate_password_hash(admin_password, rounds=10).decode("utf-8")
    admin = User(username=admin_username, password_hash=password_hash, role="admin")
    db.session.add(admin)
    db.session.commit()
