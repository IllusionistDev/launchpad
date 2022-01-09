pip install --disable-pip-version-check --exists-action w -r requirements/core.txt
python manage.py migrate
python manage.py collectstatic --no-input
# this magic command will run Dockerfile's command:
exec "$@"
