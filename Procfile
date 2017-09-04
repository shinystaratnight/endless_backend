runserver: PYTHONUNBUFFERED=true bin/django runserver 0.0.0.0:$DJANGO_UWSGI_PORT
celery: C_FORCE_ROOT=1 bin/celery worker -n worker.celery -E -A ecore -E -l info --scheduler=redbeat.RedBeatScheduler -Q celery
celery-beat: C_FORCE_ROOT=1 bin/celery beat -A ecore -l info --scheduler=redbeat.RedBeatScheduler
