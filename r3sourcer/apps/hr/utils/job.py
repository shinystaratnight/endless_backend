from datetime import timedelta, datetime, date

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone


def get_available_candidate_list(job):
    """
    Gets the list of available candidate contacts for the job fillin form
    :param job: job object
    :return: queryset of the candidate contacts
    """
    from r3sourcer.apps.candidate import models as candidate_models
    from r3sourcer.apps.core import models as core_models
    from r3sourcer.apps.hr import models as hr_models

    today = date.today()

    content_type = ContentType.objects.get_for_model(candidate_models.CandidateContact)
    objects = core_models.WorkflowObject.objects.filter(
        state__number=70,
        state__workflow__model=content_type,
        active=True,
    ).distinct('object_id').values_list('object_id', flat=True)

    candidate_contacts = candidate_models.CandidateContact.objects.filter(
        contact__is_available=True,
        candidate_skills__skill=job.position,
        candidate_skills__candidate_skill_rates__valid_from__lte=today,
        candidate_skills__candidate_skill_rates__valid_until__gte=today,
        candidate_skills__skill__active=True,
        candidate_skills__score__gt=0,
        id__in=objects
    ).distinct()

    if candidate_contacts.exists():
        blacklists_candidates = hr_models.BlackList.objects.filter(
            Q(jobsite=job.jobsite) | Q(company_contact=job.jobsite.primary_contact),
            candidate_contact__in=candidate_contacts
        ).values_list('candidate_contact', flat=True)

        candidate_contacts = candidate_contacts.exclude(id__in=blacklists_candidates)

        if job.transportation_to_work:
            candidate_contacts = candidate_contacts.filter(transportation_to_work=job.transportation_to_work)

    return candidate_contacts


def get_partially_available_candidate_ids_for_vs(candidate_contacts, shift_date, shift_time):
    """
    Get unavailable/partially available candidates for ShiftDate
    :param candidate_contacts: queryset of CandidateContacts to search for
    :param shift_start_time: shift_start_time value of ShiftDate
    :return: set of ids of unavailable or partially available recruits
    """
    from r3sourcer.apps.hr.models import JobOffer

    shift_start_time = timezone.make_aware(datetime.combine(shift_date, shift_time))

    from_date = shift_start_time - timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)
    to_date = shift_start_time + timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)
    candidate_ids = list(candidate_contacts.filter(
        Q(job_offers__shift__date__shift_date=from_date.date(),
          job_offers__shift__time__gte=from_date.timetz()) |
        Q(job_offers__shift__date__shift_date__gt=from_date.date()),
        Q(job_offers__shift__date__shift_date=to_date.date(),
          job_offers__shift__time__lte=to_date.timetz()) |
        Q(job_offers__shift__date__shift_date__lt=to_date.date())
    ).exclude(
        job_offers__status=JobOffer.STATUS_CHOICES.cancelled
    ).values_list('id', flat=True))

    candidate_ids.extend(candidate_contacts.filter(
        job_offers__time_sheets__shift_started_at__range=[from_date, to_date]
    ).values_list('id', flat=True))

    candidate_ids.extend(candidate_contacts.filter(
        contact__contact_unavailabilities__unavailable_from__lte=shift_start_time,
        contact__contact_unavailabilities__unavailable_until__gte=shift_start_time,
    ).values_list('id', flat=True))

    candidate_ids.extend(candidate_contacts.filter(
        carrier_lists__job_offer__isnull=False,
        carrier_lists__target_date=shift_date,
    ).exclude(
        carrier_lists__job_offer__status=JobOffer.STATUS_CHOICES.cancelled,
    ).values_list('id', flat=True))

    return set(candidate_ids)


def get_partially_available_candidate_ids(candidate_contacts, job_shifts):
    partial = {}

    for job_shift in job_shifts:
        vs_id, shift_time, shift_date = job_shift.id, job_shift.time, job_shift.date.shift_date
        for candidate_id in get_partially_available_candidate_ids_for_vs(candidate_contacts, shift_date, shift_time):
            if candidate_id not in partial:
                partial[candidate_id] = []
            partial[candidate_id].append(vs_id)

    return partial
