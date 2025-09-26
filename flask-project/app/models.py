from __future__ import annotations

import enum
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Enum, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Role(enum.StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class InvitationStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class TaskStatus(enum.StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class NotificationType(enum.StrEnum):
    INVITE = "invite"
    DEADLINE = "deadline"


task_members = db.Table(
    "task_members",
    db.Column("task_id", db.Integer, db.ForeignKey("tasks.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_filename = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    two_factor_secret = db.Column(db.String(32))

    owned_projects = db.relationship("Project", backref="owner", lazy="dynamic")
    memberships = db.relationship("Membership", back_populates="user", lazy="dynamic")
    tasks_created = db.relationship(
        "Task", foreign_keys="Task.created_by_id", back_populates="creator"
    )
    tasks_assigned = db.relationship(
        "Task", secondary=task_members, back_populates="assignees"
    )
    notifications = db.relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def initials(self) -> str:
        words = [part for part in self.name.strip().split() if part]
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][0].upper()
        return (words[0][0] + words[1][0]).upper()

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class OTPToken(TimestampMixin, db.Model):
    __tablename__ = "otp_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("User", backref=db.backref("otp_tokens", lazy="dynamic"))

    def is_valid(self) -> bool:
        return (not self.is_used) and datetime.utcnow() <= self.expires_at


class Project(TimestampMixin, db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    memberships = db.relationship(
        "Membership",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    tasks = db.relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
    invitations = db.relationship(
        "Invitation",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class Membership(TimestampMixin, db.Model):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_member_project"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    role = db.Column(Enum(Role), nullable=False, default=Role.MEMBER)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship("User", back_populates="memberships")
    project = db.relationship("Project", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<Membership user={self.user_id} project={self.project_id} {self.role}>"


class Invitation(TimestampMixin, db.Model):
    __tablename__ = "invitations"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    inviter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    invitee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)
    responded_at = db.Column(db.DateTime)

    project = db.relationship("Project", back_populates="invitations")
    inviter = db.relationship(
        "User", foreign_keys=[inviter_id], backref=db.backref("invitations_sent", lazy="dynamic")
    )
    invitee = db.relationship(
        "User",
        foreign_keys=[invitee_id],
        backref=db.backref("invitations_received", lazy="dynamic"),
    )

    def mark(self, status: InvitationStatus) -> None:
        self.status = status
        self.responded_at = datetime.utcnow()


class Task(TimestampMixin, db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    status = db.Column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    project = db.relationship("Project", back_populates="tasks")
    creator = db.relationship(
        "User", foreign_keys=[created_by_id], back_populates="tasks_created"
    )
    assignees = db.relationship(
        "User", secondary=task_members, back_populates="tasks_assigned"
    )

    def is_due_soon(self, threshold_days: int) -> bool:
        if not self.due_date:
            return False
        delta = self.due_date - datetime.utcnow()
        return 0 <= delta.days < threshold_days or (0 <= delta.total_seconds() <= threshold_days * 86400)


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type = db.Column(Enum(NotificationType), nullable=False)
    reference = db.Column(db.String(120), index=True)
    payload = db.Column(db.JSON, nullable=False, default=dict)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("User", back_populates="notifications")

    def mark_read(self) -> None:
        self.is_read = True


__all__ = [
    "User",
    "OTPToken",
    "Project",
    "Membership",
    "Role",
    "Task",
    "TaskStatus",
    "task_members",
    "Invitation",
    "InvitationStatus",
    "Notification",
    "NotificationType",
]

