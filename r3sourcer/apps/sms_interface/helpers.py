from django.db.models import Q
from django.utils import timezone

from .models import PhoneNumber, SMSMessage


def get_phone_number(company=None):
    qry = Q()
    if company is not None:
        qry = Q(company=company)
    return PhoneNumber.objects.filter(qry).last()


def get_sms(from_number, to_number, text, reply_timeout=None,
            check_reply=True, delivery_timeout=None, **kwargs):
    assert to_number, "Number is required"
    assert text, "Message text is required"

    params = dict(text=text, from_number=from_number,
                  to_number=to_number, check_delivered=True,
                  sent_at=timezone.now(), check_reply=check_reply,
                  type=SMSMessage.TYPE_CHOICES.SENT)

    if reply_timeout is not None:
        params['reply_timeout'] = reply_timeout

    if delivery_timeout is not None:
        params['delivery_timeout'] = delivery_timeout

    return SMSMessage(**params)
