import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.processor import process_excel
from app.models import UploadRecord
from app import db
import json

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"xlsx", "xls"}


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected.", "danger")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(request.url)

        if not _allowed(file.filename):
            flash("Only .xlsx and .xls files are accepted.", "danger")
            return redirect(request.url)

        original_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{original_name}"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
        file.save(filepath)

        try:
            results = process_excel(filepath)
        except Exception as e:
            os.remove(filepath)
            flash(f"Processing error: {str(e)}", "danger")
            return redirect(request.url)

        # Save record
        record = UploadRecord(
            filename=unique_name,
            original_name=original_name,
            uploaded_by=current_user.id,
            store_count=results["summary"]["total_stores"],
            product_count=results["summary"]["total_products"],
        )
        db.session.add(record)
        db.session.commit()

        # Store results in session (serialized summary only; full data via API)
        session["last_upload_id"] = record.id
        session["last_upload_file"] = unique_name
        session["last_summary"] = results["summary"]
        session["store_names"] = results["store_names"]

        flash(f"File processed successfully! Found {results['summary']['total_stores']} stores and {results['summary']['total_products']} products.", "success")
        return redirect(url_for("dashboard.index"))

    # GET: show upload history
    if current_user.is_admin():
        history = UploadRecord.query.order_by(UploadRecord.uploaded_at.desc()).limit(20).all()
    else:
        history = UploadRecord.query.filter_by(uploaded_by=current_user.id).order_by(UploadRecord.uploaded_at.desc()).limit(20).all()

    return render_template("upload.html", history=history)
