from django.core.exceptions import ObjectDoesNotExist

from r3sourcer.apps.sms_interface.helpers import get_language_list
from r3sourcer.apps.email_interface.models import EmailTemplate


def get_email_template(company_id, contact_id, slug):
    templates = {x.language_id: x for x in EmailTemplate.objects.filter(company_id=company_id, slug=slug).all()}
    langs = get_language_list(company_id, contact_id)
    for lang in langs:
        template = templates.get(lang)
        if template:
            return template
    raise ObjectDoesNotExist('Template not found')
