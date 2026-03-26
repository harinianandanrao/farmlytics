from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db, bcrypt
from app.email_utils import (
    send_verification_email, send_password_reset_email,
    verify_token
)

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
            if not user.is_verified:
                flash("Please verify your email before logging in. Check your inbox.", "warning")
                return render_template("login.html")
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([name, email, password, confirm]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("register.html")

        user = User(name=name, email=email, role="employee", is_verified=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        sent = send_verification_email(email, name)
        if sent:
            flash(f"Account created! Check {email} for a verification link.", "success")
        else:
            flash("Account created, but we couldn't send the verification email. Contact your admin.", "warning")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    email = verify_token(token, salt="email-verify", max_age=3600)
    if not email:
        flash("The verification link is invalid or has expired.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Account not found.", "danger")
        return redirect(url_for("auth.login"))

    if user.is_verified:
        flash("Your email is already verified. Please log in.", "info")
        return redirect(url_for("auth.login"))

    user.is_verified = True
    db.session.commit()
    flash("Email verified! You can now log in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Please enter your email address.", "danger")
            return render_template("forgot_password.html")

        user = User.query.filter_by(email=email).first()
        # Always show success message to avoid email enumeration
        if user and user.is_verified:
            send_password_reset_email(user.email, user.name)

        flash(f"If {email} is registered and verified, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = verify_token(token, salt="password-reset", max_age=1800)
    if not email:
        flash("The reset link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Account not found.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not password or not confirm:
            flash("Both fields are required.", "danger")
            return render_template("reset_password.html", token=token)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("reset_password.html", token=token)

        user.set_password(password)
        db.session.commit()
        flash("Password updated successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)


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

    user = User(name=name, email=email, role=role, is_verified=True)
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
