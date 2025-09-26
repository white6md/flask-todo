from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    Invitation,
    InvitationStatus,
    Membership,
    Notification,
    Project,
    Role,
    Task,
    TaskStatus,
    User,
)
from ..utils.email import send_email
from ..utils.notifications import notify_invitation
from .forms import InviteMemberForm, ProjectForm, TaskForm


projects_bp = Blueprint("projects", __name__, url_prefix="/projects")


def _membership_for_current_user(project_id: int) -> Membership | None:
    return Membership.query.filter_by(
        project_id=project_id, user_id=current_user.id, is_active=True
    ).first()


def _collect_members(project: Project):
    memberships = project.memberships.filter_by(is_active=True).all()
    members = {project.owner.id: project.owner}
    for membership in memberships:
        members[membership.user.id] = membership.user
    return members


@projects_bp.route("/create", methods=["POST"])
@login_required
def create_project():
    form = ProjectForm()
    wants_json = request.accept_mimetypes.accept_json and request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            description=form.description.data,
            owner_id=current_user.id,
        )
        db.session.add(project)
        db.session.flush()

        owner_membership = Membership(
            user_id=current_user.id, project_id=project.id, role=Role.OWNER
        )
        db.session.add(owner_membership)
        db.session.commit()

        if wants_json:
            project_data = {
                "id": project.id,
                "name": project.name,
                "description": project.description or "",
                "role": "owner",
                "detail_url": url_for("projects.detail", project_id=project.id),
                "tasks_total": 0,
                "tasks_done": 0,
            }
            return jsonify(success=True, message="Project created successfully.", project=project_data), 201

        flash("Project created successfully.", "success")
    else:
        if wants_json:
            return jsonify(success=False, errors=form.errors), 400
        flash("Please fix the errors in the project form.", "danger")

    return redirect(request.referrer or url_for("dashboard.home"))


@projects_bp.route("/<int:project_id>")
@login_required
def detail(project_id: int):
    project = Project.query.get_or_404(project_id)
    membership = _membership_for_current_user(project_id)
    is_owner = project.owner_id == current_user.id
    if not is_owner and not membership:
        abort(403)

    task_form = TaskForm()
    members, assign_options, _ = _prepare_task_form(task_form, project, is_owner)

    invite_form = InviteMemberForm()

    tasks = (
        Task.query.filter_by(project_id=project_id)
        .order_by(Task.due_date.asc().nulls_last(), Task.created_at.asc())
        .all()
    )

    return render_template(
        "projects/detail.html",
        project=project,
        tasks=tasks,
        task_form=task_form,
        invite_form=invite_form,
        is_owner=is_owner,
        members=members,
        assign_options=assign_options,
    )


def _parse_due_date(form: TaskForm) -> datetime | None:
    return form.due_date.data or None



def _parse_due_date(form: TaskForm) -> datetime | None:
    return form.due_date.data or None


def _prepare_task_form(
    task_form: TaskForm,
    project: Project,
    is_owner: bool,
    selected_id: int | None = None,
):
    members = _collect_members(project)
    if is_owner:
        options = [(member.id, member.name) for member in members.values()]
    else:
        options = [(current_user.id, current_user.name)]

    allowed_ids = {value for value, _ in options}
    task_form.set_assignee_choices(options)

    if task_form.is_submitted():
        submitted_value = task_form.assignee_id.data or 0
        selected_value = submitted_value if submitted_value in allowed_ids or submitted_value == 0 else 0
    elif selected_id is not None:
        selected_value = selected_id if selected_id in allowed_ids else 0
    elif not is_owner and current_user.id in allowed_ids:
        selected_value = current_user.id
    else:
        selected_value = 0

    task_form.assignee_id.data = selected_value

    return members, task_form.assignee_id.choices, allowed_ids


@projects_bp.route("/<int:project_id>/tasks", methods=["POST"])


@projects_bp.route("/<int:project_id>/tasks", methods=["POST"])
@login_required
def create_task(project_id: int):
    project = Project.query.get_or_404(project_id)
    membership = _membership_for_current_user(project_id)
    is_owner = project.owner_id == current_user.id
    if not is_owner and not membership:
        abort(403)

    task_form = TaskForm()
    _, _, allowed_ids = _prepare_task_form(task_form, project, is_owner)

    if task_form.validate_on_submit():
        assignee_id = task_form.assignee_id.data or 0
        if assignee_id and assignee_id not in allowed_ids:
            flash("Members can only assign tasks to themselves.", "danger")
            return redirect(url_for("projects.detail", project_id=project_id))

        assignee = User.query.get(assignee_id) if assignee_id else None

        task = Task(
            project_id=project_id,
            title=task_form.title.data,
            description=task_form.description.data,
            due_date=_parse_due_date(task_form),
            status=TaskStatus(task_form.status.data),
            created_by_id=current_user.id,
            assigned_to_id=assignee.id if assignee else None,
        )
        task.assignees = [assignee] if assignee else []
        db.session.add(task)
        db.session.commit()
        flash("Task created.", "success")
    else:
        flash("Unable to create task. Please review the form.", "danger")

    return redirect(url_for("projects.detail", project_id=project_id))


@projects_bp.route("/<int:project_id>/tasks/<int:task_id>", methods=["POST"])
@login_required
def update_task(project_id: int, task_id: int):
    project = Project.query.get_or_404(project_id)
    membership = _membership_for_current_user(project_id)
    is_owner = project.owner_id == current_user.id
    if not is_owner and not membership:
        abort(403)

    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    task_form = TaskForm()
    current_assignee_id = task.assigned_to_id or (task.assignees[0].id if task.assignees else 0)
    _, _, allowed_ids = _prepare_task_form(task_form, project, is_owner, current_assignee_id)

    if task_form.validate_on_submit():
        assignee_id = task_form.assignee_id.data or 0
        if assignee_id and assignee_id not in allowed_ids:
            flash("Members can only assign tasks to themselves.", "danger")
            return redirect(url_for("projects.detail", project_id=project_id))

        current_access_ids = {user.id for user in task.assignees}
        if not current_access_ids and task.assigned_to_id:
            current_access_ids = {task.assigned_to_id}
        if not is_owner and task.created_by_id != current_user.id and current_user.id not in current_access_ids:
            flash("Members can edit only their tasks.", "danger")
            return redirect(url_for("projects.detail", project_id=project_id))

        assignee = User.query.get(assignee_id) if assignee_id else None

        task.title = task_form.title.data
        task.description = task_form.description.data
        task.due_date = _parse_due_date(task_form)
        task.status = TaskStatus(task_form.status.data)
        task.assignees = [assignee] if assignee else []
        task.assigned_to_id = assignee.id if assignee else None
        db.session.commit()
        flash("Task updated.", "success")
    else:
        flash("Update failed. Please review the form.", "danger")

    return redirect(url_for("projects.detail", project_id=project_id))


@projects_bp.route("/<int:project_id>/tasks/<int:task_id>/move", methods=["POST"])
@login_required
def move_task(project_id: int, task_id: int):
    project = Project.query.get_or_404(project_id)
    membership = _membership_for_current_user(project_id)
    is_owner = project.owner_id == current_user.id
    if not is_owner and not membership:
        abort(403)

    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    data = request.get_json(silent=True) or {}
    status_value = data.get("status")

    try:
        new_status = TaskStatus(status_value)
    except ValueError:
        return {"error": "Invalid status"}, 400

    # Allow any active project member to move tasks; ownership already checked above
    task.status = new_status
    db.session.commit()
    return {"status": task.status.value}


@projects_bp.route("/<int:project_id>/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(project_id: int, task_id: int):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash("Only project owners can delete tasks.", "danger")
        return redirect(url_for("projects.detail", project_id=project_id))

    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("projects.detail", project_id=project_id))


@projects_bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        abort(403)

    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "info")
    return redirect(url_for("dashboard.home"))


@projects_bp.route("/<int:project_id>/invite", methods=["POST"])
@login_required
def invite_member(project_id: int):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        abort(403)

    form = InviteMemberForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("This email is not registered.", "danger")
            return redirect(url_for("projects.detail", project_id=project_id))

        existing_membership = Membership.query.filter_by(
            user_id=user.id, project_id=project_id, is_active=True
        ).first()
        if existing_membership:
            flash("User is already a member of this project.", "info")
            return redirect(url_for("projects.detail", project_id=project_id))

        existing_invitation = Invitation.query.filter_by(
            project_id=project_id,
            invitee_id=user.id,
            status=InvitationStatus.PENDING,
        ).first()
        if existing_invitation:
            flash("Invitation already sent.", "warning")
            return redirect(url_for("projects.detail", project_id=project_id))

        invitation = Invitation(
            project_id=project_id,
            inviter_id=current_user.id,
            invitee_id=user.id,
        )
        db.session.add(invitation)
        db.session.commit()

        notify_invitation(invitation)
        send_email(
            subject=f"You've been invited to {project.name}",
            recipients=[user.email],
            body=(
                f"Hello {user.name},\n\n"
                f"{current_user.name} invited you to collaborate on '{project.name}'.\n"
                "Visit your dashboard to respond to this invitation."
            ),
        )

        flash("Invitation sent.", "success")
    else:
        flash("Invalid email address.", "danger")

    return redirect(url_for("projects.detail", project_id=project_id))


@projects_bp.route("/invitations/<int:invitation_id>/<string:action>", methods=["POST"])
@login_required
def handle_invitation(invitation_id: int, action: str):
    invitation = Invitation.query.get_or_404(invitation_id)
    if invitation.invitee_id != current_user.id:
        abort(403)
    if invitation.status != InvitationStatus.PENDING:
        flash("This invitation has already been handled.", "info")
        return redirect(url_for("dashboard.notifications"))

    if action == "accept":
        invitation.mark(InvitationStatus.ACCEPTED)
        membership = Membership.query.filter_by(
            user_id=current_user.id, project_id=invitation.project_id
        ).first()
        if not membership:
            membership = Membership(
                user_id=current_user.id,
                project_id=invitation.project_id,
                role=Role.MEMBER,
            )
            db.session.add(membership)
        else:
            membership.is_active = True
        flash("Invitation accepted.", "success")
    elif action == "decline":
        invitation.mark(InvitationStatus.DECLINED)
        flash("Invitation declined.", "info")
    else:
        flash("Unknown action.", "danger")

    Notification.query.filter_by(
        reference=f"invite:{invitation.id}", user_id=current_user.id
    ).delete(synchronize_session=False)

    db.session.commit()
    return redirect(request.referrer or url_for("dashboard.notifications"))


