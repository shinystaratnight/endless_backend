from celery import shared_task
from celery.utils.log import get_task_logger

from .exceptions import SMSServiceError
from .utils import get_sms_service


logger = get_task_logger(__name__)


@shared_task(bind=True)
def fetch_remote_sms(self):
    try:
        sms_service = get_sms_service()
        sms_service.fetch()
    except SMSServiceError as e:
        logger.exception('Cannot fetch SMS messages. Error: %s', e)
