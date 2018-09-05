from r3sourcer.apps.core.api.router import router

from r3sourcer.apps.core.api import endpoints as core_endpoints
from r3sourcer.apps.candidate import models as candidate_models
from r3sourcer.apps.candidate.api import viewsets as candidate_viewsets, filters as candidate_filters
from r3sourcer.apps.candidate.api import serializers as candidate_serializers


class CandidateContactEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.CandidateContact
    base_viewset = candidate_viewsets.CandidateContactViewset
    serializer = candidate_serializers.CandidateContactSerializer
    filter_class = candidate_filters.CandidateContactFilter

    search_fields = (
        'contact__title', 'contact__last_name', 'contact__first_name', 'contact__address__city__search_names',
        'contact__address__street_address',
    )


class SkillRelEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.SkillRel
    serializer = candidate_serializers.SkillRelSerializer
    filter_class = candidate_filters.SkillRelFilter


class TagRelEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.TagRel
    serializer = candidate_serializers.TagRelSerializer
    filter_class = candidate_filters.TagRelFilter


class SubcontractorEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.Subcontractor
    base_viewset = candidate_viewsets.SubcontractorViewset
    serializer = candidate_serializers.SubcontractorSerializer


class SubcontractorCandidateRelationEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.SubcontractorCandidateRelation
    serializer = candidate_serializers.SubcontractorCandidateRelationSerializer


class SuperannuationFundEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.SuperannuationFund
    search_fields = ['name']
    serializer_fields = ('id', 'name', 'membership_number', 'phone', 'website')


class VisaTypeEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.VisaType
    serializer_fields = ('id', 'subclass', 'name', 'general_type', 'work_hours_allowed', 'is_available')


class CandidateLocationEndpoint(core_endpoints.ApiEndpoint):

    model = candidate_models.CandidateContact
    base_viewset = candidate_viewsets.CandidateLocationViewset
    serializer_fields = ('id', )


router.register(endpoint=VisaTypeEndpoint())
router.register(endpoint=SuperannuationFundEndpoint())
router.register(endpoint=CandidateContactEndpoint())
router.register(endpoint=SubcontractorEndpoint())
router.register(endpoint=TagRelEndpoint())
router.register(endpoint=SkillRelEndpoint())
router.register(candidate_models.InterviewSchedule)
router.register(candidate_models.CandidateRel)
router.register(endpoint=SubcontractorCandidateRelationEndpoint())
router.register(endpoint=CandidateLocationEndpoint(), url='candidate/location')
