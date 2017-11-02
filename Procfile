runserver: PYTHONUNBUFFERED=true bin/django runserver 0.0.0.0:$DJANGO_UWSGI_PORT
celery: C_FORCE_ROOT=1 bin/celery worker -n worker.celery -E -A r3sourcer -E -l info --scheduler=redbeat.RedBeatScheduler -Q celery
celery-beat: C_FORCE_ROOT=1 bin/celery beat -A r3sourcer -l info --scheduler=redbeat.RedBeatScheduler
