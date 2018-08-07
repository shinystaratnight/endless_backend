import math

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import PhoneNumber, SMSMessage
from r3sourcer.apps.core.models.core import Company


def get_phone_number(company=None):
    qry = Q()
    if company is not None:
        qry = Q(company=company)
    return PhoneNumber.objects.filter(qry).last()


def get_sms(from_number, to_number, text, reply_timeout=None,
            check_reply=True, delivery_timeout=None, **kwargs):
    assert to_number, "Number is required"
    assert text, "Message text is required"

    number_of_segments = math.ceil(len(text) / settings.SMS_SEGMENT_SIZE)
    company = Company.objects.get(twilio_credentials__accounts_list__phone_numbers__phone_number=from_number)
    company.sms_balance.substract_sms_cost(number_of_segments)
    params = dict(text=text, from_number=from_number,
                  to_number=to_number, check_delivered=True,
                  sent_at=timezone.now(), check_reply=check_reply,
                  type=SMSMessage.TYPE_CHOICES.SENT,
                  company=company, segments=number_of_segments)

    if reply_timeout is not None:
        params['reply_timeout'] = reply_timeout

    if delivery_timeout is not None:
        params['delivery_timeout'] = delivery_timeout

    return SMSMessage(**params)
