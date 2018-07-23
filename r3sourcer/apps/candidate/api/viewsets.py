from django.utils.translation import ugettext_lazy as _

import stripe

from rest_framework import status, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response

from r3sourcer.apps.billing.models import Payment
from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.core.models import Company, InvoiceRule

from . import serializers
from ..models import Subcontractor, CandidateContactAnonymous, CandidateRel
from ..tasks import buy_candidate


class CandidateContactViewset(BaseApiViewset):

    @action(methods=['post'], detail=False)
    def register(self, request, *args, **kwargs):
        serializer = serializers.CandidateContactRegisterSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        serializer = serializers.CandidateContactSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    @action(methods=['get'], detail=True)
    def profile(self, request, pk, *args, **kwargs):
        return self.retrieve(request, pk=pk, *args, **kwargs)

    @action(methods=['post'], detail=False)
    def sendsms(self, request, *args, **kwargs):
        id_list = request.data

        if not id_list or not isinstance(id_list, list):
            raise exceptions.ParseError(_('You should select Company addresses'))

        phone_numbers = set(self.model.objects.filter(
            id__in=id_list, contact__phone_mobile__isnull=False).values_list(
            'contact__phone_mobile', flat=True))

        return Response({
            'status': 'success',
            'phone_number': phone_numbers,
            'message': _('Phones numbers was selected'),
        })

    @action(methods=['get'], detail=False)
    def pool(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            queryset = CandidateContactAnonymous.objects.none()
        else:
            company = request.user.contact.get_closest_company()
            queryset = CandidateContactAnonymous.objects.exclude(
                candidate_rels__master_company=company
            ).distinct()
        return self._paginate(request, serializers.CandidatePoolSerializer, self.filter_queryset(queryset))

    @action(methods=['post'], detail=True)
    def buy(self, request, pk, *args, **kwargs):
        candidate_contact = self.get_object()
        company = request.data.get('company')

        try:
            company = Company.objects.get(pk=company)
        except Company.DoesNotExist:
            raise exceptions.ValidationError({'company': _('Cannot find company')})

        existing_rel = CandidateRel.objects.filter(
            master_company=company, candidate_contact=candidate_contact
        ).first()
        if existing_rel:
            raise exceptions.ValidationError({'company': _('Company already has this Candidate Contact')})

        if not company.stripe_customer:
            raise exceptions.ValidationError({'company': _('Company has no billing information')})

        if candidate_contact.profile_price:
            rel = CandidateRel.objects.create(
                master_company=company, candidate_contact=candidate_contact, owner=False, active=False
            )

            buy_candidate.apply_async([rel.id], countdown=10)

        return Response({'status': 'success', 'message': _('Please wait for payment to complete')})


class SubcontractorViewset(BaseApiViewset):

    http_method_names = ['post', 'put', 'get', 'options']

    @action(methods=['post'], detail=False)
    def register(self, request, *args, **kwargs):
        serializer = serializers.CandidateContactRegisterSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        candidate = serializer.save()
        company = Company.objects.create(
            name=str(candidate),
            expense_account='6-1006'
        )

        instance = Subcontractor.objects.create(
            company=company,
            primary_contact=candidate
        )

        InvoiceRule.objects.create(company=company)

        serializer = serializers.SubcontractorSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)
