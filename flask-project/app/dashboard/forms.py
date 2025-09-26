from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import FileField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length


class ProfileForm(FlaskForm):
    name = StringField("Display Name", validators=[DataRequired(), Length(max=120)])
    submit = SubmitField("Save Changes")


class AvatarForm(FlaskForm):
    avatar = FileField("Profile Picture")
    submit = SubmitField("Upload")


class PasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("new_password")]
    )
    submit = SubmitField("Update Password")
