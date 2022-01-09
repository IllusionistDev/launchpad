
import uuid
import logging

from django.db import models
from django.utils import timezone

from catalog import Catalog, App

logger = logging.getLogger(__name__)


def default_expiry():
    return timezone.now() + timezone.timedelta(hours=1)


class SessionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(expires_at__gt=timezone.now())

    def expired(self):
        return self.filter(expires_at__lte=timezone.now())

    def get_or_none(self, **filter_criteria):
        self.objects.filter(**filter_criteria).first()


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    expires_at = models.DateTimeField(default=default_expiry)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = SessionQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    @classmethod
    def get_or_create_session(cls, session_id=None):
        if session_id:
            try:
                return cls.objects.get(session_id=session_id)
            except cls.DoesNotExist:
                logger.info("Session '%s' is not found. Creating new one.", session_id)

        return cls.objects.create()

    @classmethod
    def get_valid_apps(self):
        return Catalog.get_valid_apps()

    @classmethod
    def install_app(cls, app_name, session_id=None):
        """
        Creates session and install an app for it.
        """
        # create anonymous session if not already
        session = cls.get_or_create_session(session_id=session_id)
        # launch app into the cluster
        app = Catalog.install_app(app_name, session=session)
        # track launched app information
        launched_app, __ = LaunchedApp.objects.update_or_create(
            app_name=app_name, created_by=session,
            defaults={
                'url': app.details['app_url'],
                'status': app.details['status'],
                'status_updated_at': app.details['last_checked_at'],
            }
        )
        return launched_app

    @classmethod
    def uninstall(cls, app_name, session_id):
        """
        Uninstall an app for a session.
        """
        # create anonymous session if not already
        session = Session.objects.get_or_none(session_id=session_id)
        if session:
            app = LaunchedApp.objects.get_or_none(app_name=app_name, session=session)
            if app:
                # uninstall app from the cluster
                Catalog.uninstall_app(app, session=session)
                # delete the launched app instance
                app.delete()
        return session


class LaunchedAppQueryset(models.QuerySet):
    def get_or_none(self, **filter_criteria):
        self.objects.filter(**filter_criteria).first() 


class LaunchedApp(models.Model):
    created_by = models.ForeignKey(Session, related_name='apps', on_delete=models.CASCADE)
    app_name = models.CharField(max_length=255, choices=App.choices, default=App.VSCODE)

    url = models.URLField(max_length=255)
    status = models.CharField(max_length=255)
    status_updated_at = models.DateTimeField(null=True, blank=True)

    launched_at = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = LaunchedAppQueryset.as_manager()

    def __str__(self):
        return f"<{self.app} | status: {self.status} @ {self.status_updated_at} | launched @ {self.launched_at}>"
