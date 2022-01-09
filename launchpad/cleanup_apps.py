import sys
import logging

from launch_vscode import VSCode

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    with open('./installed_apps.txt', 'r') as fp:
        for session in fp.read().split():
            if session := session.strip():
                logger.info("\n\n")
                logger.info("=========================================")
                logger.info("Cleaning up the session: %s", session)
                logger.info("=========================================")

                vscode_app = VSCode(session=session)
                vscode_app.uninstall(wait_until_uninstalled=True)

                logger.info("=========================================")
                logger.info("Cleaned up the session: %s", session)
                logger.info("=========================================")
                logger.info("\n\n")
