from __future__ import annotations

import base64
import io
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
from ..models import User
from .forms import (
    LoginForm,
    RegistrationForm,
    TwoFactorForm,
)


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")






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
            user.is_verified = True
            db.session.commit()

            flash("Account created. Please sign in to continue.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)



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
        else:
            if not user.is_verified:
                user.is_verified = True
                db.session.commit()
            if not user.two_factor_secret:
                session["setup_2fa_user_id"] = user.id
                flash("Scan the QR code to finish securing your account.", "info")
                return redirect(url_for("auth.setup_2fa"))
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
