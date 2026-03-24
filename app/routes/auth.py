from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db, bcrypt

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        flash("Password reset instructions sent to your email (demo mode).", "info")
        return redirect(url_for("auth.login"))
    return render_template("forgot_password.html")


@auth_bp.route("/admin/users", methods=["GET"])
@login_required
def manage_users():
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.index"))
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("manage_users.html", users=users)


@auth_bp.route("/admin/users/create", methods=["POST"])
@login_required
def create_user():
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.index"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "employee")

    if not all([name, email, password]):
        flash("All fields are required.", "danger")
        return redirect(url_for("auth.manage_users"))

    if User.query.filter_by(email=email).first():
        flash("A user with that email already exists.", "danger")
        return redirect(url_for("auth.manage_users"))

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"User {name} created successfully.", "success")
    return redirect(url_for("auth.manage_users"))


@auth_bp.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.index"))

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("auth.manage_users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.name} deleted.", "success")
    return redirect(url_for("auth.manage_users"))
