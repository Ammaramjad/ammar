import csv
import io
import json
import os
from datetime import datetime
from uuid import uuid4

import pandas as pd
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename

from . import bcrypt, db
from .ml import (
    REQUIRED_FEATURE_COLUMNS,
    load_model_artifact,
    preprocess_prediction_data,
    preprocess_training_data,
    save_model_artifact,
    serialize_log,
    train_models,
    validate_columns,
)
from .models import DatasetUpload, ModelRun, PredictionRecord, User

auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint("main", __name__)


@main_bp.before_app_request
def keep_session_fresh() -> None:
    from flask import session

    session.permanent = True


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "warning")
            return redirect(url_for("auth.register"))

        password_hash = bcrypt.generate_password_hash(password, rounds=10).decode("utf-8")
        user = User(username=username, password_hash=password_hash, role="instructor")
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid credentials.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have logged out.", "info")
    return redirect(url_for("auth.login"))


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    datasets = DatasetUpload.query.filter_by(user_id=current_user.id, upload_type="training").order_by(
        DatasetUpload.created_at.desc()
    )
    latest_model = ModelRun.query.order_by(ModelRun.created_at.desc()).first()
    latest_prediction = (
        PredictionRecord.query.filter_by(user_id=current_user.id).order_by(PredictionRecord.created_at.desc()).first()
    )
    latest_batch_id = latest_prediction.batch_id if latest_prediction else None
    latest_predictions = []
    if latest_batch_id:
        latest_predictions = (
            PredictionRecord.query.filter_by(user_id=current_user.id, batch_id=latest_batch_id)
            .order_by(PredictionRecord.student_id.asc())
            .all()
        )

    counts = {"Excellent": 0, "Average": 0, "At-Risk": 0}
    for record in latest_predictions:
        counts[record.predicted_label] = counts.get(record.predicted_label, 0) + 1

    return render_template(
        "dashboard.html",
        datasets=datasets,
        latest_model=latest_model,
        latest_predictions=latest_predictions,
        prediction_counts=counts,
        latest_batch_id=latest_batch_id,
    )


@main_bp.route("/upload-training", methods=["POST"])
@login_required
def upload_training():
    file = request.files.get("training_file")
    if not file or file.filename == "":
        flash("Please select a CSV file for training.", "danger")
        return redirect(url_for("main.dashboard"))

    if not file.filename.lower().endswith(".csv"):
        flash("Invalid file type. Upload a CSV file.", "danger")
        return redirect(url_for("main.dashboard"))

    filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    destination = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(destination)

    frame = pd.read_csv(destination)
    missing_columns = validate_columns(frame, include_target=False)
    if missing_columns:
        os.remove(destination)
        flash(f"Missing required columns: {', '.join(missing_columns)}", "danger")
        return redirect(url_for("main.dashboard"))

    upload = DatasetUpload(
        user_id=current_user.id,
        filename=filename,
        path=destination,
        upload_type="training",
        preprocessing_log=json.dumps(["File uploaded and schema validated."]),
    )
    db.session.add(upload)
    db.session.commit()
    flash("Training dataset uploaded successfully.", "success")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/train-model", methods=["POST"])
@login_required
def train_model():
    dataset_id = request.form.get("dataset_id", type=int)
    dataset = DatasetUpload.query.filter_by(id=dataset_id, user_id=current_user.id, upload_type="training").first()
    if not dataset:
        flash("Selected training dataset was not found.", "danger")
        return redirect(url_for("main.dashboard"))

    frame = pd.read_csv(dataset.path)
    missing_columns = validate_columns(frame, include_target=False)
    if missing_columns:
        flash(f"Dataset is missing required columns: {', '.join(missing_columns)}", "danger")
        return redirect(url_for("main.dashboard"))

    x_data, y_data, preprocess_artifacts = preprocess_training_data(frame)
    result, trained_models = train_models(x_data, y_data)

    model_artifact = {
        "model": trained_models[result.selected_model_name],
        "scaler": preprocess_artifacts["scaler"],
        "feature_columns": REQUIRED_FEATURE_COLUMNS,
        "feature_means": preprocess_artifacts["feature_means"],
        "selected_model_name": result.selected_model_name,
        "trained_at": datetime.utcnow().isoformat(),
    }
    save_model_artifact(current_app.config["MODEL_ARTIFACT_PATH"], model_artifact)

    dataset.preprocessing_log = serialize_log(preprocess_artifacts["preprocessing_log"])
    model_run = ModelRun(
        dataset_upload_id=dataset.id,
        selected_model=result.selected_model_name,
        accuracy=result.selected_metrics["accuracy"],
        precision=result.selected_metrics["precision"],
        recall=result.selected_metrics["recall"],
        f1_score=result.selected_metrics["f1_score"],
    )
    db.session.add(model_run)
    db.session.commit()

    flash(
        f"Model training completed. Best model: {result.selected_model_name} "
        f"(Accuracy: {result.selected_metrics['accuracy']:.2%})",
        "success",
    )
    return redirect(url_for("main.dashboard"))


@main_bp.route("/predict", methods=["POST"])
@login_required
def predict():
    if not os.path.exists(current_app.config["MODEL_ARTIFACT_PATH"]):
        flash("Train a model before generating predictions.", "warning")
        return redirect(url_for("main.dashboard"))

    file = request.files.get("prediction_file")
    if not file or file.filename == "":
        flash("Please select a CSV file for prediction.", "danger")
        return redirect(url_for("main.dashboard"))

    if not file.filename.lower().endswith(".csv"):
        flash("Invalid file type. Upload a CSV file.", "danger")
        return redirect(url_for("main.dashboard"))

    filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    destination = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(destination)

    frame = pd.read_csv(destination)
    missing_columns = validate_columns(frame, include_target=False)
    if missing_columns:
        os.remove(destination)
        flash(f"Missing required columns: {', '.join(missing_columns)}", "danger")
        return redirect(url_for("main.dashboard"))

    upload = DatasetUpload(
        user_id=current_user.id,
        filename=filename,
        path=destination,
        upload_type="prediction",
        preprocessing_log=json.dumps(["Prediction file uploaded and validated."]),
    )
    db.session.add(upload)
    db.session.flush()

    artifact = load_model_artifact(current_app.config["MODEL_ARTIFACT_PATH"])
    x_prediction = preprocess_prediction_data(frame, artifact["feature_means"], artifact["scaler"])
    predictions = artifact["model"].predict(x_prediction)
    batch_id = uuid4().hex

    prediction_rows = []
    student_ids = frame["student_id"].astype(str) if "student_id" in frame.columns else frame.index.astype(str)
    for idx, label in enumerate(predictions):
        prediction_rows.append(
            PredictionRecord(
                user_id=current_user.id,
                batch_id=batch_id,
                student_id=student_ids.iloc[idx] if hasattr(student_ids, "iloc") else student_ids[idx],
                predicted_label=str(label),
            )
        )
    db.session.add_all(prediction_rows)
    db.session.commit()

    flash(f"Generated predictions for {len(prediction_rows)} students.", "success")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/export/<batch_id>/csv")
@login_required
def export_csv(batch_id: str):
    records = (
        PredictionRecord.query.filter_by(user_id=current_user.id, batch_id=batch_id)
        .order_by(PredictionRecord.student_id.asc())
        .all()
    )
    if not records:
        flash("No predictions found for selected batch.", "warning")
        return redirect(url_for("main.dashboard"))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["batch_id", "student_id", "predicted_label", "generated_at"])
    for record in records:
        writer.writerow([record.batch_id, record.student_id, record.predicted_label, record.created_at.isoformat()])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=prediction_{batch_id}.csv"},
    )


@main_bp.route("/export/<batch_id>/pdf")
@login_required
def export_pdf(batch_id: str):
    records = (
        PredictionRecord.query.filter_by(user_id=current_user.id, batch_id=batch_id)
        .order_by(PredictionRecord.student_id.asc())
        .all()
    )
    if not records:
        flash("No predictions found for selected batch.", "warning")
        return redirect(url_for("main.dashboard"))

    counts = {"Excellent": 0, "Average": 0, "At-Risk": 0}
    for record in records:
        counts[record.predicted_label] = counts.get(record.predicted_label, 0) + 1

    pdf_path = os.path.join(current_app.instance_path, f"prediction_{batch_id}.pdf")
    pdf_canvas = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    y = height - 50

    pdf_canvas.setFont("Helvetica-Bold", 14)
    pdf_canvas.drawString(50, y, "Smart Student Performance Prediction Report")
    y -= 30
    pdf_canvas.setFont("Helvetica", 10)
    pdf_canvas.drawString(50, y, f"Generated on: {datetime.utcnow().isoformat()} UTC")
    y -= 20
    pdf_canvas.drawString(50, y, f"Batch ID: {batch_id}")
    y -= 20
    pdf_canvas.drawString(50, y, f"Total Students: {len(records)}")
    y -= 20
    pdf_canvas.drawString(
        50,
        y,
        f"Excellent: {counts.get('Excellent', 0)} | Average: {counts.get('Average', 0)} | At-Risk: {counts.get('At-Risk', 0)}",
    )
    y -= 30

    pdf_canvas.setFont("Helvetica-Bold", 10)
    pdf_canvas.drawString(50, y, "Student ID")
    pdf_canvas.drawString(260, y, "Predicted Category")
    y -= 15
    pdf_canvas.setFont("Helvetica", 10)

    for record in records:
        if y < 50:
            pdf_canvas.showPage()
            y = height - 50
        pdf_canvas.drawString(50, y, str(record.student_id))
        pdf_canvas.drawString(260, y, record.predicted_label)
        y -= 14

    pdf_canvas.save()
    return send_file(pdf_path, as_attachment=True, download_name=f"prediction_{batch_id}.pdf")
