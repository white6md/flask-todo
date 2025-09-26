from __future__ import annotations

from flask import flash, redirect, url_for
from flask_babel import Babel
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
babel = Babel()
csrf = CSRFProtect()


login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


@login_manager.unauthorized_handler
def handle_unauthorized():
    flash("Please log in to access this page.", "warning")
    return redirect(url_for("auth.login"))


def select_locale() -> str:
    return "en"


__all__ = [
    "db",
    "login_manager",
    "mail",
    "migrate",
    "babel",
    "csrf",
    "select_locale",
]
