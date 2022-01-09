import logging

from launchpad import celery_app
from catalog import VSCode

from .models import Session

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_sessions():
    for session in Session.objects.expired():
        logger.info("\n\n")
        logger.info("=========================================")
        logger.info("Cleaning up the session: %s", session)
        logger.info("=========================================")

        app = VSCode(session=str(session))
        app.uninstall(wait_until_uninstalled=True)

        logger.info("=========================================")
        logger.info("Cleaned up the session: %s", session)
        logger.info("=========================================")
        logger.info("\n\n")


@celery_app.task
def update_app_details_for_active_sessions():
    for session in Session.objects.active():
        logger.info("\n\n")
        logger.info("============================================")
        logger.info("Updating app status for session: %s", session)
        logger.info("============================================")

        app = VSCode(session=str(session))
        app.update_app_details_from_cluster()

        logger.info("===========================================")
        logger.info("Updated app status for session: %s", session)
        logger.info("===========================================")
        logger.info("\n\n")
