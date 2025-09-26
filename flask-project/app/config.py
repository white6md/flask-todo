from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    APP_NAME = os.environ.get("APP_NAME", "Todo-List")
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{(INSTANCE_DIR / 'app.db').resolve().as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    OTP_EXPIRATION_MINUTES = int(os.environ.get("OTP_EXPIRATION_MINUTES", 10))
    TASK_DEADLINE_WARNING_DAYS = int(os.environ.get("TASK_DEADLINE_WARNING_DAYS", 2))


    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", str((BASE_DIR / "static" / "img" / "avatars").resolve())
    )
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    SESSION_COOKIE_SECURE = False
