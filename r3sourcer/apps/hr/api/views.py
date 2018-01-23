from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.utils import vacancy as vacancy_utils
from r3sourcer.apps.hr.utils.utils import calculate_distances_for_jobsite


class CandidateDistanceView(APIView):

    def post(self, request, *args, **kwargs):
        vacancy = request.data.get('vacancy', None)
        candidate_contacts = request.data.get('contacts', [])
        distances = []
        if vacancy and candidate_contacts:
            vacancy = hr_models.Vacancy.objects.get(id=vacancy)
            contacts = core_models.Contact.objects.filter(candidate_contacts__id__in=candidate_contacts)
            calculate_distances_for_jobsite(contacts, vacancy.jobsite)

        for candidate in candidate_models.CandidateContact.objects.filter(id__in=candidate_contacts):
            matrix = vacancy.get_distance_matrix(candidate)
            if matrix:
                distances.append({'contact': candidate.id, **matrix})

        return Response(distances)


class AvailableCandidatesDateView(APIView):

    def post(self, request, *args, **kwargs):
        vacancy = request.data.get("vacancy", None)
        shifts = request.data.get("shifts", None)
        result = []
        if vacancy:
            vacancy = hr_models.Vacancy.objects.get(pk=vacancy)
            vacancy_shifts = hr_models.Shift.objects.filter(id__in=shifts, date__vacancy=vacancy)
            candidate_contacts = vacancy_utils.get_available_candidate_list(vacancy)

            partially_available = vacancy_utils.get_partially_available_candidate_ids(
                candidate_contacts, vacancy_shifts
            )
            result = [
                partial for partial, dates in partially_available.items()
                if len(dates) == vacancy_shifts.count()
            ]
        return Response({'result': result})
