from flask import Flask
from flask_login import current_user
from .config import Config
from .extensions import babel, csrf, db, login_manager, mail, migrate, select_locale
from .utils.translations import translate


def create_app(config_class: type[Config] | None = None) -> Flask:
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(config_class or Config)

    register_extensions(app)
    register_blueprints(app)
    register_context_processors(app)

    with app.app_context():
        db.create_all()
        from .models import Task, User

        pending = (
            Task.query.filter(Task.assigned_to_id.isnot(None))
            .filter(~Task.assignees.any())
            .all()
        )
        if pending:
            for task in pending:
                user = User.query.get(task.assigned_to_id)
                if user and user not in task.assignees:
                    task.assignees.append(user)
            db.session.commit()

    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    babel.init_app(app, locale_selector=select_locale)
    csrf.init_app(app)


@login_manager.user_loader
def load_user(user_id: str):
    from .models import User

    return User.query.get(int(user_id))


def register_blueprints(app: Flask) -> None:
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .projects.routes import projects_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp)


def register_context_processors(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = sum(1 for n in current_user.notifications if not n.is_read)
        return {
            "t": lambda key, **kwargs: translate(key, **kwargs),
            "current_lang": "en",
            "app_name": app.config.get("APP_NAME", "Todo-List"),
            "unread_notifications_count": unread_count,
        }
