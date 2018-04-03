import os
from datetime import timedelta
from celery.schedules import crontab

from kombu import Queue, Exchange


def env(key, default=None):
    return os.environ.get(key, default)


result_backend = 'django-db'

broker_url = 'amqp://{host}:{port}//'.format(
    host=env('RABBIT_MQ_HOST'),
    port=env('RABBIT_MQ_PORT'),
)
redbeat_redis_url = 'redis://{host}:{port}/{db}'.format(
    host=env('REDIS_HOST'),
    port=env('REDIS_PORT'),
    db=env('REDIS_BEAT_DB'),
)

timezone = env('TIME_ZONE')
accept_content = ['json', 'application/text']
broker_transport_options = {'visibility_timeout': 2 * 60 * 60}

task_queues = (
    Queue('celery', Exchange('celery'), routing_key='celery'),
    Queue('sms', Exchange('sms'), routing_key='sms'),
    Queue('hr', Exchange('hr'), routing_key='hr'),
)

task_routes = {
    'r3sourcer.apps.sms_interface.tasks.fetch_remote_sms': {
        'queue': 'sms',
    },
}

beat_schedule = {
    'fetch_twilio_accounts': {
        'task': 'r3sourcer.apps.sms_interface.tasks.fetch_remote_sms',
        'schedule': timedelta(seconds=60),
    },
    'check_unpaid_invoices': {
        'task': 'r3sourcer.apps.hr.tasks.check_unpaid_invoices',
        'schedule': crontab(hour=5, minute=00),
    },
    'sync_to_myob': {
        'task': 'r3sourcer.apps.myob.tasks.sync_to_myob',
        'schedule': crontab(minute=0, hour=1),
    },
    'sync_timesheets': {
        'task': 'r3sourcer.apps.myob.tasks.sync_timesheets',
        'schedule': crontab(minute=0, hour='2-23'),
    },
    'update_all_distances': {
        'task': 'r3sourcer.apps.hr.tasks.update_all_distances',
        'schedule': crontab(minute=0, hour=22, day_of_week='fri,sat')
    },
}

task_ignore_result = True
task_store_errors_even_if_ignored = True
