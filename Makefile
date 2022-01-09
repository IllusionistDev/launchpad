up:
	docker-compose up --remove-orphans

up-d:
	docker-compose up -d --remove-orphans

stop:
	docker-compose stop

restart:
	docker-compose restart

down:
	docker-compose down

logs:
	docker-compose logs -f -t 500 web

clogs:
	docker-compose logs -f -t 500 celery

ssh:
	docker-compose exec web /bin/bash

cssh:
	docker-compose exec celery /bin/bash

shell:
	docker-compose exec web /bin/bash -c "python manage.py shell"

requirements:
	docker-compose exec web /bin/bash -c "pip install --disable-pip-version-check --exists-action w -r requirements/core.txt -r requirements/dev.txt"

test:
	docker-compose exec web /bin/bash -c "python manage.py test"

flake8:
	docker-compose exec web /bin/bash -c "flake8 --ignore=E999 --max-line-length=120 --exclude core/tests,core/migrations"
