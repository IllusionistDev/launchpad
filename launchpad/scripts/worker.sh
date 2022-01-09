pip install --disable-pip-version-check --exists-action w -r requirements/core.txt
celery -A launchpad worker --concurrency=3 -Ofair -E -l info
