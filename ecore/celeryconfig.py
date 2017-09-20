import os

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
    # TODO: create
    # Queue('example', Exchange('example'), routing_key='example')
)
task_routes = {}

beat_schedule = {}
