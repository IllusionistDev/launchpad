pip install --disable-pip-version-check --exists-action w -r requirements.txt
watchmedo auto-restart --directory=/launchpad/ --pattern=*.py --recursive -- celery -A launchpad beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
