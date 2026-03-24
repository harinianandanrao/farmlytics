from flask import Blueprint, render_template, session, redirect, url_for
from flask_login import login_required, current_user
from app.models import UploadRecord

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    summary = session.get("last_summary", {})
    store_names = session.get("store_names", [])
    upload_id = session.get("last_upload_id")

    recent_upload = None
    if upload_id:
        recent_upload = UploadRecord.query.get(upload_id)

    return render_template(
        "dashboard.html",
        summary=summary,
        store_names=store_names,
        recent_upload=recent_upload,
        has_data=bool(summary),
    )


@dashboard_bp.route("/explorer")
@login_required
def explorer():
    store_names = session.get("store_names", [])
    return render_template("explorer.html", store_names=store_names, has_data=bool(store_names))


@dashboard_bp.route("/reports")
@login_required
def reports():
    summary = session.get("last_summary", {})
    store_names = session.get("store_names", [])
    upload_id = session.get("last_upload_id")
    recent_upload = UploadRecord.query.get(upload_id) if upload_id else None
    return render_template("reports.html", summary=summary, store_names=store_names, recent_upload=recent_upload, has_data=bool(summary))


@dashboard_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")
