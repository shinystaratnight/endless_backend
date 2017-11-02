from django.conf import settings
from django.db import transaction

from celery import shared_task
from celery.utils.log import get_task_logger
from phonenumber_field import phonenumber

from r3sourcer.apps.core.service import factory
from r3sourcer.apps.core.models import Contact

from .models import TokenLogin


logger = get_task_logger(__name__)


def get_contact(contact_id):
    try:
        contact = Contact.objects.get(id=contact_id)
    except Contact.DoesNotExist as e:
        logger.exception(e)
    else:
        return contact


def send_login_token(contact, send_func, tpl, redirect_url=None,
                     type=TokenLogin.TYPES.sms):
    with transaction.atomic():
        token_login = TokenLogin.objects.create(
            contact=contact, type=type, redirect_to=redirect_url
        )

        data_dict = dict(
            contact=contact,
            auth_url="%s%s" % (settings.SITE_URL, token_login.auth_url),
            project_url=settings.SITE_URL,
        )

        logger.info('Prepared Login token for contact %s. URL: %s',
                    contact, data_dict['auth_url'])

        send_func(to_number=contact.phone_mobile, tpl_name=tpl, **data_dict)


@shared_task(bind=True)
def send_login_sms(self, contact_id, redirect_url=None):
    sms_interface = factory.get_instance(
        getattr(settings, 'SMS_INTERFACE_CLASS', 'sms_interface')
    )

    sms_tpl = 'login-sms-token'

    contact = get_contact(contact_id)
    if contact is not None:
        send_login_token(
            contact, sms_interface.send_tpl, sms_tpl, redirect_url
        )


@shared_task(bind=True)
def send_login_email(self, contact_id):
    email_interface = factory.get_instance(
        getattr(settings, 'EMAIL_INTERFACE_CLASS', 'email_interface')
    )

    # FIXME: get valid sms template
    email_tpl = ''

    contact = get_contact(contact_id)
    if contact is not None:
        send_login_token(
            contact, email_interface.send_tpl, email_tpl,
            TokenLogin.TYPES.email
        )


def send_login_message(username, contact):
    phone_number = phonenumber.to_python(username)
    if not phone_number or not phone_number.is_valid():
        send_login_email.delay(contact.id)
    else:
        send_login_sms.delay(contact.id)
