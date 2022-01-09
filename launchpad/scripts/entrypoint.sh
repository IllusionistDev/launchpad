pip install --disable-pip-version-check --exists-action w -r requirements/core.txt
python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py createsuperuser --username admin --email admin@example.com --no-input --verbosity 3
# this magic command will run Dockerfile's command:
exec "$@"
