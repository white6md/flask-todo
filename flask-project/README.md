# Todo-List

Todo-List is a Flask-based project and task manager that combines collaborative boards, deadline reminders, notifications, and two-factor authentication into a single, modern interface.

## Features
- Multi-project dashboard with live metrics and modal project creation.
- Kanban-style task board with drag-and-drop status updates.
- Team management with project invitations and role-aware access.
- Email and in-app notifications for invites and upcoming deadlines.
- Optional two-factor authentication using TOTP codes and QR provisioning.

## Prerequisites
- Python 3.10 or newer
- pip (Python package manager)
- (Optional) SQLite CLI tools if you want to inspect the default `instance/app.db`

## Initial Setup
1. Clone the repository and enter the project folder.
2. Create a virtual environment:
   - Windows: `python -m venv .venv`
   - macOS/Linux: `python3 -m venv .venv`
3. Activate the virtual environment:
   - Windows PowerShell: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
4. Install the Python dependencies:
   `pip install -r requirements.txt`

## Running the Application
- Development server with auto-reload:
  `flask --app run.py --debug run`
- Alternatively, run the app module directly:
  `python run.py`
- Visit `http://127.0.0.1:5000/` in your browser.

## Common Commands
- Create a migration after model changes: `flask --app run.py db migrate -m "Message"`
- Apply migrations: `flask --app run.py db upgrade`
- Launch an interactive shell with app context: `flask --app run.py shell`

## Project Structure (excerpt)
```
app/
  __init__.py        # Application factory and blueprint registration
  config.py          # Configuration classes and defaults
  extensions.py      # SQLAlchemy, Migrate, Mail, Babel, Login manager instances
  models.py          # Database models for User, Project, Task, Notifications, etc.
  auth/              # Authentication and 2FA routes/forms
  dashboard/         # Dashboard, profile, notifications routes/forms
  projects/          # Project and task management routes/forms
static/
  css/style.css      # Global styles (light theme overrides and components)
  js/main.js         # Front-end interactions (modals, drag-drop, AJAX)
templates/           # Jinja templates (base layout, dashboard, auth, projects)
instance/app.db      # SQLite database (development sample)
.env                  # Environment configuration
run.py                # Entry point that creates the Flask app
```

## Notes and Tips
- Drag-and-drop task moves rely on the `/projects/<id>/tasks/<task_id>/move` endpoint. Ensure JavaScript is enabled for column counts to update live.
- Translations live in `app/utils/translations.py`. Update or extend the dictionary to localize new UI strings.
- Email notifications require working SMTP credentials. In development you can swap `MAIL_SERVER` to `localhost` and use a tool like MailHog.
- Avatar uploads are saved under `static/img/avatar`. Confirm the directory is writable when deploying.

## Troubleshooting
- If you encounter `RuntimeError: Working outside of application context`, run the command with `flask --app run.py ...` so the app factory is used.
- A 403 when dragging tasks usually means the current user is not part of the project. Invite or log in with a member that has access.
- For migrations, make sure `instance` exists; Flask-Migrate will create `app.db` automatically after `db upgrade`.

Enjoy building with Todo-List!
