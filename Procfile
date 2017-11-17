runserver: PYTHONUNBUFFERED=true bin/django runserver 0.0.0.0:$DJANGO_UWSGI_PORT
celery: bin/celery worker -n worker.celery -E -A r3sourcer -E -l info --scheduler=redbeat.RedBeatScheduler
celery-beat: bin/celery beat -A r3sourcer -l info --scheduler=redbeat.RedBeatScheduler
