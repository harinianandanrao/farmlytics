from itsdangerous import URLSafeTimedSerializer
from flask import current_app, url_for
from flask_mail import Message
from app import mail


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_token(email, salt):
    return _serializer().dumps(email, salt=salt)


def verify_token(token, salt, max_age=3600):
    try:
        email = _serializer().loads(token, salt=salt, max_age=max_age)
        return email
    except Exception:
        return None


def send_verification_email(user_email, user_name):
    token = generate_token(user_email, salt="email-verify")
    verify_url = url_for("auth.verify_email", token=token, _external=True)

    msg = Message(
        subject="Verify your Farmlytics account",
        recipients=[user_email],
    )
    msg.html = f"""
    <div style="font-family:Inter,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#0B1F3A;color:#fff;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <div style="width:52px;height:52px;background:#00C896;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;color:#fff;">F</div>
        <h2 style="color:#fff;margin:12px 0 4px;">Farmlytics</h2>
        <p style="color:#94a3b8;margin:0;">Retail Price Intelligence Platform</p>
      </div>
      <h3 style="color:#fff;margin-bottom:8px;">Hi {user_name},</h3>
      <p style="color:#cbd5e1;line-height:1.6;">Thanks for signing up! Please verify your email address to activate your account.</p>
      <div style="text-align:center;margin:32px 0;">
        <a href="{verify_url}" style="background:#00C896;color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">Verify Email Address</a>
      </div>
      <p style="color:#64748b;font-size:13px;">This link expires in <strong>1 hour</strong>. If you didn't create an account, you can ignore this email.</p>
      <hr style="border-color:#1e3a5f;margin:24px 0;"/>
      <p style="color:#64748b;font-size:12px;text-align:center;">Farmlytics &mdash; Retail Price Intelligence</p>
    </div>
    """
    try:
        mail.send(msg)
        return True
    except Exception:
        return False


def send_password_reset_email(user_email, user_name):
    token = generate_token(user_email, salt="password-reset")
    reset_url = url_for("auth.reset_password", token=token, _external=True)

    msg = Message(
        subject="Reset your Farmlytics password",
        recipients=[user_email],
    )
    msg.html = f"""
    <div style="font-family:Inter,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#0B1F3A;color:#fff;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <div style="width:52px;height:52px;background:#00C896;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;color:#fff;">F</div>
        <h2 style="color:#fff;margin:12px 0 4px;">Farmlytics</h2>
        <p style="color:#94a3b8;margin:0;">Retail Price Intelligence Platform</p>
      </div>
      <h3 style="color:#fff;margin-bottom:8px;">Hi {user_name},</h3>
      <p style="color:#cbd5e1;line-height:1.6;">You requested a password reset. Click the button below to set a new password.</p>
      <div style="text-align:center;margin:32px 0;">
        <a href="{reset_url}" style="background:#E74C3C;color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">Reset Password</a>
      </div>
      <p style="color:#64748b;font-size:13px;">This link expires in <strong>30 minutes</strong>. If you didn't request this, ignore this email — your password won't change.</p>
      <hr style="border-color:#1e3a5f;margin:24px 0;"/>
      <p style="color:#64748b;font-size:12px;text-align:center;">Farmlytics &mdash; Retail Price Intelligence</p>
    </div>
    """
    try:
        mail.send(msg)
        return True
    except Exception:
        return False
