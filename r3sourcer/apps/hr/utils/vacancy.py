from datetime import timedelta, datetime

from django.conf import settings
from django.db.models import Q
from django.utils import timezone


def get_partially_available_candidate_ids_for_vs(candidate_contacts, shift_date, shift_time):
    """
    Get unavailable/partially available candidates for VacancyDate
    :param candidate_contacts: queryset of CandidateContacts to search for
    :param shift_start_time: shift_start_time value of VacancyDate
    :return: set of ids of unavailable or partially available recruits
    """
    from r3sourcer.apps.hr.models import VacancyOffer

    shift_start_time = timezone.make_aware(datetime.combine(shift_date, shift_time))

    from_date = shift_start_time - timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)
    to_date = shift_start_time + timedelta(hours=settings.VACANCY_FILLING_TIME_DELTA)
    candidate_ids = list(candidate_contacts.filter(
        Q(vacancy_offers__shift__date__shift_date=from_date.date(),
          vacancy_offers__shift__time__gte=from_date.timetz()) |
        Q(vacancy_offers__shift__date__shift_date__gt=from_date.date()),
        Q(vacancy_offers__shift__date__shift_date=to_date.date(),
          vacancy_offers__shift__time__lte=to_date.timetz()) |
        Q(vacancy_offers__shift__date__shift_date__lt=to_date.date())
    ).exclude(
        vacancy_offers__status=VacancyOffer.STATUS_CHOICES.cancelled
    ).values_list('id', flat=True))

    candidate_ids.extend(candidate_contacts.filter(
        vacancy_offers__time_sheets__shift_started_at__range=[from_date, to_date]
    ).values_list('id', flat=True))

    candidate_ids.extend(candidate_contacts.filter(
        contact__contact_unavailabilities__unavailable_from__lte=shift_start_time,
        contact__contact_unavailabilities__unavailable_until__gte=shift_start_time,
    ).values_list('id', flat=True))

    candidate_ids.extend(candidate_contacts.filter(
        carrier_lists__vacancy_offer__isnull=False,
        carrier_lists__target_date=shift_date,
    ).exclude(
        carrier_lists__vacancy_offer__status=VacancyOffer.STATUS_CHOICES.cancelled,
    ).values_list('id', flat=True))

    return set(candidate_ids)


def get_partially_available_candidate_ids(candidate_contacts, vacancy_shifts):
    partial = {}

    for vacancy_shift in vacancy_shifts:
        vs_id, shift_time, shift_date = vacancy_shift.id, vacancy_shift.time, vacancy_shift.date.shift_date
        for candidate_id in get_partially_available_candidate_ids_for_vs(candidate_contacts, shift_date, shift_time):
            if candidate_id not in partial:
                partial[candidate_id] = []
            partial[candidate_id].append(vs_id)

    return partial
