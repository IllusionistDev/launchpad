import enum
from core.models import LaunchedApp, Session

from .vscode import VSCode

__all__ = ['VSCode', 'Catalog', 'App']


class App(enum.Enum):
    VSCODE = 'vscode'

    @classmethod
    def to_enum_item(cls, app_name):
        all_apps = cls.all()
        assert app_name in all_apps, f"The app '{app_name}' is not supported."
        return all_apps[app_name]

    @classmethod
    def all(cls):
        return {member.value: member for __, member in cls.__members__.items()}

    @classmethod
    def choices(cls):
        return [(app_name, app_name) for app_name in cls.all()]


class Catalog:
    """
    Catalog for supported app's wide operations.
    """
    app_classes = {
        App.VSCODE: VSCode
    }

    @classmethod
    def get_valid_apps(self):
        return list(App.all().keys())

    @classmethod
    def install_app(cls, app_name: str, session: Session, **app_kwargs):
        """
        Launches app into the cluster.
        """
        app_enum = App.to_enum_item(app_name)
        app_class = cls.app_classes[app_enum]
        app_instance = app_class(session=str(session), **app_kwargs)
        app_instance.launch(wait_for_readiness=True)
        return app_instance

    @classmethod
    def uninstall_app(cls, app_name: LaunchedApp, session: Session, **app_kwargs):
        """
        Uninstall app from the cluster.
        """
        app_enum = App.to_enum_item(app_name)
        app_class = cls.app_classes[app_enum]
        app_instance = app_class(session=str(session), **app_kwargs)
        app_instance.uninstall(wait_until_uninstalled=True)
