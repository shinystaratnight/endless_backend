from django.conf import settings
from django.db import transaction
from django.utils import module_loading

from celery import shared_task
from celery.utils.log import get_task_logger

from r3sourcer.apps.core.service import factory
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.candidate import models as candidate_models


logger = get_task_logger(__name__)


@shared_task(bind=True)
def send_verify_sms(self, candidate_contact_id, workflow_object_id=None):
    try:
        sms_interface = module_loading.import_string(settings.SMS_SERVICE_CLASS)()
    except ImportError:
        logger.exception('Cannot load SMS service')
        return

    sms_tpl = 'mobile-phone-verification'

    try:
        candidate = candidate_models.CandidateContact.objects.get(id=candidate_contact_id)
    except candidate_models.CandidateContact.DoesNotExist as e:
        logger.exception(e)
        candidate = None

    if candidate is not None:
        with transaction.atomic():
            data_dict = dict(
                contact=candidate.contact,
                manager=candidate.recruitment_agent or candidate.get_closest_company().manager
            )

            if workflow_object_id is not None:
                workflow_object = core_models.WorkflowObject.objects.get(id=workflow_object_id)
                data_dict['related_objs'] = [workflow_object]

            logger.info('Sending phone verify SMS to %s.', candidate.contact)

            sms_interface.send_tpl(
                to_number=candidate.contact.phone_mobile, tpl_name=sms_tpl, related_obj=candidate, **data_dict
            )
