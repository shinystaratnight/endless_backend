import math

from django.conf import settings
from django.db.models import Q

from r3sourcer.apps.candidate.models import CandidateContactLanguage
from r3sourcer.apps.core.models import CompanyLanguage
from r3sourcer.apps.sms_interface.models import PhoneNumber, SMSMessage, SMSTemplate
from r3sourcer.helpers.datetimes import utc_now


def get_phone_number(company=None):
    qry = Q()
    if company is not None:
        qry = Q(company=company)
    return PhoneNumber.objects.filter(qry).last()


def get_sms(from_number, to_number, text, reply_timeout=None,
            check_reply=True, delivery_timeout=None, company=None, **kwargs):
    assert to_number, "Number is required"
    assert text, "Message text is required"

    number_of_segments = math.ceil(len(text) / settings.SMS_SEGMENT_SIZE)
    params = dict(
        text=text,
        from_number=from_number,
        to_number=to_number,
        check_delivered=True,
        sent_at=utc_now(),
        check_reply=check_reply,
        type=SMSMessage.TYPE_CHOICES.SENT,
        company=company,
        segments=number_of_segments,
        template=kwargs.get('template'),
    )

    if reply_timeout is not None:
        params['reply_timeout'] = reply_timeout

    if delivery_timeout is not None:
        params['delivery_timeout'] = delivery_timeout

    return SMSMessage(**params)


def get_sms_template(company_id, candidate_contact_id, slug):
    candidate_languages = CandidateContactLanguage.objects.filter(candidate_contact_id=candidate_contact_id).all()
    company_languages = CompanyLanguage.objects.filter(company_id=company_id).all()
    default_candidate_lang, *_ = [x for x in candidate_languages if x.default is True] or [None]
    candidate_langs = [x for x in candidate_languages if x.default is False]
    default_company_lang, *_ = [x for x in company_languages if x.default is True] or [None]
    same_lang = set([x.language_id for x in candidate_languages]) & set([x.language_id for x in company_languages])
    if default_candidate_lang is not None \
            and default_candidate_lang.language_id in [x.language_id for x in company_languages]:
        language = default_candidate_lang.language_id
    elif default_company_lang is not None \
            and default_company_lang.language_id in [x.language_id for x in candidate_langs]:
        language = default_company_lang.language_id
    elif same_lang:
        language = sorted(same_lang)[-1]
    elif default_company_lang:
        language = default_company_lang.language_id
    else:
        language = settings.DEFAULT_LANGUAGE

    return SMSTemplate.objects.get(company_id=company_id,
                                   language_id=language,
                                   slug=slug)
