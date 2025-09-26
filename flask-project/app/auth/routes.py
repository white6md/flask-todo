from __future__ import annotations

import base64
import io
import secrets
from datetime import datetime, timedelta

import pyotp
import qrcode
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import OTPToken, User
from ..utils.email import send_email
from .forms import (
    LoginForm,
    OTPVerificationForm,
    RegistrationForm,
    ResendOTPForm,
    TwoFactorForm,
)


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _create_otp(user: User) -> OTPToken:
    OTPToken.query.filter_by(user_id=user.id, is_used=False).update({"is_used": True})
    code = _generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(
        minutes=current_app.config["OTP_EXPIRATION_MINUTES"]
    )
    token = OTPToken(user_id=user.id, code=code, expires_at=expires_at)
    db.session.add(token)
    db.session.commit()
    return token


def _send_otp_email(user: User, code: str) -> None:
    subject = "Your verification code"
    body = (
        f"Hello {user.name},\n\n"
        f"Use the following verification code to complete your registration: {code}\n\n"
        "The code expires in a few minutes."
    )
    send_email(subject=subject, recipients=[user.email], body=body)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if user and user.is_verified:
            flash("Email is already registered.", "danger")
        else:
            if not user:
                user = User(email=email, name=form.name.data)
                db.session.add(user)
            else:
                user.name = form.name.data

            user.set_password(form.password.data)
            user.is_verified = False
            db.session.commit()

            otp = _create_otp(user)
            _send_otp_email(user, otp.code)

            session["pending_user_id"] = user.id
            flash("Verification code sent. Please check your email.", "info")
            return redirect(url_for("auth.verify_otp"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    form = OTPVerificationForm()
    resend_form = ResendOTPForm()
    user_id = session.get("pending_user_id")
    if not user_id:
        flash("No pending verification found. Please register first.", "warning")
        return redirect(url_for("auth.register"))

    user = User.query.get_or_404(user_id)

    if form.validate_on_submit():
        code = form.code.data
        token = (
            OTPToken.query.filter_by(user_id=user.id, code=code, is_used=False)
            .order_by(OTPToken.created_at.desc())
            .first()
        )
        if not token or not token.is_valid():
            flash("Invalid or expired code.", "danger")
        else:
            token.is_used = True
            user.is_verified = True
            db.session.commit()
            session.pop("pending_user_id", None)
            session["setup_2fa_user_id"] = user.id
            flash("Email verified! Let's secure your account.", "success")
            return redirect(url_for("auth.setup_2fa"))

    if resend_form.validate_on_submit():
        otp = _create_otp(user)
        _send_otp_email(user, otp.code)
        flash("A new code has been sent to your email.", "info")

    return render_template(
        "auth/verify_otp.html", form=form, resend_form=resend_form, email=user.email
    )


def _build_totp_qr_data(user: User) -> str:
    if not user.two_factor_secret:
        user.two_factor_secret = pyotp.random_base32()
        db.session.commit()

    totp = pyotp.TOTP(user.two_factor_secret)
    issuer = current_app.config.get("APP_NAME", "Flask Todo Pro")
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name=issuer)

    img = qrcode.make(provisioning_uri)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}", provisioning_uri


@auth_bp.route("/setup-2fa", methods=["GET", "POST"])
def setup_2fa():
    user_id = session.get("setup_2fa_user_id")
    if current_user.is_authenticated and not user_id:
        user_id = current_user.id
    if not user_id:
        flash("No user pending two-factor setup.", "warning")
        return redirect(url_for("auth.login"))

    user = User.query.get_or_404(user_id)
    form = TwoFactorForm()
    qr_data, provisioning_uri = _build_totp_qr_data(user)

    if form.validate_on_submit():
        token = form.token.data
        totp = pyotp.TOTP(user.two_factor_secret)
        if totp.verify(token, valid_window=1):
            session.pop("setup_2fa_user_id", None)
            flash("Two-factor authentication enabled. You can log in now.", "success")
            return redirect(url_for("auth.login"))
        flash("Invalid authenticator code. Please try again.", "danger")

    return render_template(
        "auth/setup_2fa.html",
        form=form,
        qr_data=qr_data,
        provisioning_uri=provisioning_uri,
        email=user.email,
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(form.password.data):
            flash("Invalid credentials.", "danger")
        elif not user.is_verified:
            session["pending_user_id"] = user.id
            flash("Please verify your email first.", "warning")
            return redirect(url_for("auth.verify_otp"))
        elif not user.two_factor_secret:
            session["setup_2fa_user_id"] = user.id
            flash("Please finish setting up two-factor authentication.", "info")
            return redirect(url_for("auth.setup_2fa"))
        else:
            session["pre_2fa_user_id"] = user.id
            flash("Enter your authenticator code to continue.", "info")
            return redirect(url_for("auth.verify_2fa"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    user_id = session.get("pre_2fa_user_id")
    if not user_id:
        flash("Start by logging in first.", "warning")
        return redirect(url_for("auth.login"))

    user = User.query.get_or_404(user_id)
    form = TwoFactorForm()
    if form.validate_on_submit():
        token = form.token.data
        totp = pyotp.TOTP(user.two_factor_secret)
        if totp.verify(token, valid_window=1):
            login_user(user)
            session.pop("pre_2fa_user_id", None)
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard.home"))
        flash("Invalid authenticator code.", "danger")

    return render_template("auth/verify_2fa.html", form=form, email=user.email)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
