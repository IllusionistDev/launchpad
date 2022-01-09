import logging

from launchpad import celery_app

from .models import Session

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_sessions():
    for session in Session.objects.expired().with_launched_apps():
        session_id = session.id
        logger.info("Cleaning up the session: %s", session_id)
        # uninstall all the apps from expired session.
        for app in session.apps.all():
            app.uninstall()
        # delete expired session now.
        session.delete()
        logger.info("Cleaned up the session: %s", session_id)


@celery_app.task
def update_app_details_for_active_sessions():
    for session in Session.objects.active().with_launched_apps():
        logger.info("Updating app status for session: %s", session)
        for app in session.apps.all():
            app.update_from_cluster()
        logger.info("Updated app status for session: %s", session)
