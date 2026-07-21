from datetime import datetime

from flask_login import UserMixin

from . import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="instructor")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    uploads = db.relationship("DatasetUpload", backref="owner", lazy=True)


class DatasetUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    upload_type = db.Column(db.String(20), nullable=False)  # training or prediction
    preprocessing_log = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ModelRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_upload_id = db.Column(db.Integer, db.ForeignKey("dataset_upload.id"), nullable=False)
    selected_model = db.Column(db.String(120), nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    precision = db.Column(db.Float, nullable=False)
    recall = db.Column(db.Float, nullable=False)
    f1_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PredictionRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    batch_id = db.Column(db.String(64), nullable=False, index=True)
    student_id = db.Column(db.String(120), nullable=False)
    predicted_label = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
