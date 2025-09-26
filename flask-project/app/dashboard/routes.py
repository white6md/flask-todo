from __future__ import annotations

from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Notification, NotificationType, Project, Role, TaskStatus
from ..projects.forms import ProjectForm
from ..utils.notifications import ensure_deadline_notifications
from .forms import AvatarForm, PasswordForm, ProfileForm


dashboard_bp = Blueprint("dashboard", __name__)


def _collect_projects() -> list[dict[str, object]]:
    owned_projects = (
        current_user.owned_projects.order_by(Project.created_at.desc()).all()
        if hasattr(current_user.owned_projects, "order_by")
        else list(current_user.owned_projects)
    )

    entries: list[dict[str, object]] = []
    project_ids: set[int] = set()

    for project in owned_projects:
        entries.append({"project": project, "role": "owner"})
        project_ids.add(project.id)

    membership_entries = (
        current_user.memberships.filter_by(is_active=True).all()
        if hasattr(current_user.memberships, "filter_by")
        else list(current_user.memberships)
    )

    for membership in membership_entries:
        project = membership.project
        if not project or project.id in project_ids:
            continue
        role = "owner" if membership.role == Role.OWNER else "member"
        entries.append({"project": project, "role": role})
        project_ids.add(project.id)

    entries.sort(
        key=lambda item: getattr(item["project"], "created_at", None) or item["project"].id,
        reverse=True,
    )
    return entries


@dashboard_bp.route("/")
@login_required
def home():
    ensure_deadline_notifications(current_user)

    project_form = ProjectForm()
    projects = _collect_projects()
    deadline_notifications = (
        Notification.query.filter_by(
            user_id=current_user.id, type=NotificationType.DEADLINE
        )
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    total_tasks = 0
    completed_tasks = 0
    owned_count = sum(1 for entry in projects if entry["role"] == "owner")
    for entry in projects:
        project = entry.get("project")
        for task in getattr(project, "tasks", []):
            total_tasks += 1
            if task.status == TaskStatus.DONE:
                completed_tasks += 1
    active_tasks = total_tasks - completed_tasks
    stats = {
        "projects": len(projects),
        "owned": owned_count,
        "total_tasks": total_tasks,
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
    }

    return render_template(
        "dashboard/home.html",
        project_form=project_form,
        projects=projects,
        deadline_notifications=deadline_notifications,
        stats=stats,
    )


def _allowed_file(filename: str) -> bool:
    if not filename:
        return False
    allowed_extensions = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


@dashboard_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile_form = ProfileForm(obj=current_user)
    avatar_form = AvatarForm()
    password_form = PasswordForm()

    handled = False

    if profile_form.submit.data and profile_form.validate_on_submit():
        current_user.name = profile_form.name.data
        db.session.commit()
        flash("Profile updated.", "success")
        handled = True

    if avatar_form.submit.data and avatar_form.validate_on_submit():
        file = request.files.get(avatar_form.avatar.name)
        if file and _allowed_file(file.filename):
            filename = f"user_{current_user.id}_{file.filename}"
            upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
            upload_folder.mkdir(parents=True, exist_ok=True)
            file_path = upload_folder / filename
            file.save(file_path)
            current_user.avatar_filename = filename
            db.session.commit()
            flash("Avatar updated.", "success")
            handled = True
        else:
            flash("Unsupported file type.", "danger")

    if password_form.submit.data and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("Password changed successfully.", "success")
            handled = True

    if handled:
        return redirect(url_for("dashboard.profile"))

    return render_template(
        "dashboard/profile.html",
        profile_form=profile_form,
        avatar_form=avatar_form,
        password_form=password_form,
    )


@dashboard_bp.route("/notifications")
@login_required
def notifications():
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("dashboard/notifications.html", notifications=notifications)


@dashboard_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id: int):
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first_or_404()
    notification.is_read = True
    db.session.commit()
    flash("Notification marked as read.", "info")
    return redirect(request.referrer or url_for("dashboard.notifications"))
