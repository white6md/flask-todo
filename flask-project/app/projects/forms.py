from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

from ..models import TaskStatus


class ProjectForm(FlaskForm):
    name = StringField("Project Name", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    submit = SubmitField("Create")


class InviteMemberForm(FlaskForm):
    email = StringField("Member Email", validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField("Invite")


class TaskForm(FlaskForm):
    title = StringField("Task Title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Details", validators=[Length(max=1000)])
    due_date = DateTimeLocalField(
        "Due Date", format="%Y-%m-%dT%H:%M", validators=[Optional()], default=None
    )
    status = SelectField(
        "Status",
        choices=[(status.value, status.name.replace("_", " ").title()) for status in TaskStatus],
        default=TaskStatus.TODO.value,
    )
    assignee_id = SelectField("Assign To", choices=[], coerce=int, default=0)
    submit = SubmitField("Save Task")

    def set_assignee_choices(self, members: list[tuple[int, str]]) -> None:
        self.assignee_id.choices = [(0, "Unassigned"), *members]


__all__ = ["ProjectForm", "InviteMemberForm", "TaskForm"]
