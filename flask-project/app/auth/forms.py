from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")


class OTPVerificationForm(FlaskForm):
    code = StringField("Verification Code", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify")


class ResendOTPForm(FlaskForm):
    submit = SubmitField("Resend Code")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Continue")


class TwoFactorForm(FlaskForm):
    token = StringField("Authenticator Code", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify")
