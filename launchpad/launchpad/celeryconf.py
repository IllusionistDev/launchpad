import logging
import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "launchpad.settings")

app = Celery('launchpad')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'update-app-details-for-active-sessions': {
        'task': 'core.tasks.update_app_details_for_active_sessions',
        'schedule': crontab(
            minute=0,
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
    },
    'cleanup-expired-sessions': {
        'task': 'core.tasks.cleanup_expired_sessions',
        'schedule': crontab(
            minute=0,
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
    }
} if settings.ENABLE_CELERY_PERIODIC_TASKS else {}
