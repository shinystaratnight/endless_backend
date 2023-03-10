celery worker -n worker.celery -E -A r3sourcer -l info --pool=solo -Q celery,sms,hr
celery worker -n worker.celery -E -A r3sourcer -l info --pool=solo --scheduler=redbeat.RedBeatScheduler -Q celery,sms,hr

celery beat -A r3sourcer -l info --scheduler=redbeat.RedBeatScheduler