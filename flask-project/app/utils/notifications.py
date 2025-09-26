from __future__ import annotations

from datetime import datetime, timedelta

from flask import current_app

from ..extensions import db
from ..models import (
    Invitation,
    Notification,
    NotificationType,
    Project,
    Role,
    Task,
    task_members,
)


def notify_invitation(invitation: Invitation) -> None:
    reference = f"invite:{invitation.id}"
    payload = {
        "invitation_id": invitation.id,
        "project_id": invitation.project_id,
        "project_name": invitation.project.name,
        "inviter_name": invitation.inviter.name,
    }
    notification = Notification.query.filter_by(
        user_id=invitation.invitee_id, reference=reference
    ).first()
    if not notification:
        notification = Notification(
            user_id=invitation.invitee_id,
            type=NotificationType.INVITE,
            reference=reference,
            payload=payload,
        )
        db.session.add(notification)
    else:
        notification.is_read = False
        notification.payload = payload
    db.session.commit()


def ensure_deadline_notifications(user) -> None:
    threshold = current_app.config.get("TASK_DEADLINE_WARNING_DAYS", 2)
    now = datetime.utcnow()
    window_end = now + timedelta(days=threshold)

    owner_tasks = (
        Task.query.join(Project)
        .filter(
            Project.owner_id == user.id,
            Task.due_date.isnot(None),
            Task.due_date >= now,
            Task.due_date <= window_end,
        )
        .all()
    )

    member_tasks = (
        Task.query.join(task_members, Task.id == task_members.c.task_id)
        .filter(
            task_members.c.user_id == user.id,
            Task.due_date.isnot(None),
            Task.due_date >= now,
            Task.due_date <= window_end,
        )
        .all()
    )

    relevant_tasks = {task.id: task for task in owner_tasks + member_tasks}

    for task in relevant_tasks.values():
        reference = f"deadline:{task.id}:{user.id}"
        payload = {
            "task_id": task.id,
            "project_id": task.project_id,
            "task_title": task.title,
            "due": task.due_date.isoformat() if task.due_date else None,
            "project_name": task.project.name,
        }
        notification = Notification.query.filter_by(
            user_id=user.id, reference=reference
        ).first()
        if not notification:
            notification = Notification(
                user_id=user.id,
                type=NotificationType.DEADLINE,
                reference=reference,
                payload=payload,
            )
            db.session.add(notification)
        else:
            notification.payload = payload
            notification.is_read = False

    db.session.commit()
