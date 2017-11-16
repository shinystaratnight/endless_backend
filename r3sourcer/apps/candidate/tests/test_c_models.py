import datetime

import pytest
from mock import patch, MagicMock, PropertyMock

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.candidate.models import (
    InterviewSchedule, CandidateRel, AcceptanceTestQuestionRel,
    AcceptanceTestRel, CandidateContact, SkillRel, Subcontractor
)
from r3sourcer.apps.hr import models as hr_models


@pytest.mark.django_db
class TestVisaType:
    def test_visatype_str(self, visa_type):
        assert str(visa_type) == '{}: {} ({})'.format(
            visa_type.subclass, visa_type.name, visa_type.general_type)


@pytest.mark.django_db
class TestSuperannuationFund:
    def test_superannuation_fund_str(self, superannuation_fund):
        assert str(superannuation_fund) == superannuation_fund.name


@pytest.mark.django_db
class TestCandidateContact:
    def test_candidate_contact_str(self, candidate):
        assert str(candidate) == str(candidate.contact)

    def test_is_personal_info_filled_unsuccessful(self, candidate):
        candidate.transportation_to_work = None
        candidate.save()
        assert not candidate.is_personal_info_filled()

    def test_is_personal_info_filled_successful(self, candidate):
        assert candidate.is_personal_info_filled()

    def test_is_contact_info_filled_successful(self, candidate):
        assert candidate.is_contact_info_filled()

    def test_is_contact_info_filled_unsuccessful(self, candidate):
        candidate.contact.last_name = None
        assert not candidate.is_contact_info_filled()

    def test_is_email_set_successful(self, candidate):
        candidate.contact.email = "test@test.test"
        assert candidate.is_email_set()

    def test_is_email_set_unsuccessful(self, candidate):
        candidate.contact.email = None
        assert not candidate.is_email_set()

    def test_is_phone_set_successful(self, candidate):
        candidate.contact.phone_mobile = "123456789"
        assert candidate.is_phone_set()

    def test_is_phone_set_unsuccessful(self, candidate):
        candidate.contact.phone_mobile = None
        assert not candidate.is_phone_set()

    def test_is_birthday_set_successful(self, candidate):
        candidate.contact.birthday = "123456789"
        assert candidate.is_birthday_set()

    def test_is_birthday_set_unsuccessful(self, candidate):
        candidate.contact.birthday = None
        assert not candidate.is_birthday_set()

    def test_set_contact_unavailable(self, candidate):
        candidate.contact.is_available = True
        candidate.contact.save()
        candidate.set_contact_unavailable()
        assert not candidate.contact.is_available

    def test_is_address_set_successful(self, candidate, address):
        candidate.contact.address = address
        candidate.contact.save()
        assert candidate.is_address_set()

    def test_is_address_set_unsuccessful(self, candidate):
        assert not candidate.is_address_set()

    def test_is_skill_defined_successful(self, candidate, skill_rel):
        assert candidate.is_skill_defined()

    def test_is_skill_defined_unsuccessful(self, candidate):
        assert not candidate.is_skill_defined()

    def test_is_formalities_filled_successful(self, candidate):
        assert candidate.is_formalities_filled()

    def test_is_formalities_filled_unsuccessful(self, candidate):
        candidate.bank_account = None
        assert not candidate.is_formalities_filled()

    def test_are_skill_rates_set_successful(self, candidate, skill_rate_rel):
        assert candidate.are_skill_rates_set()

    def test_are_skill_rates_set_unsuccessful(self, candidate, skill_rate_rel):
        skill_rate_rel.valid_until = timezone.now() - datetime.timedelta(days=1)
        skill_rate_rel.save()
        assert not candidate.are_skill_rates_set()

    def test_are_tags_verified_unsuccessful(self, candidate, tag_rel):
        assert not candidate.are_tags_verified()

    def test_are_tags_verified_successful(self, candidate, tag_rel, user, company_contact):
        request = MagicMock()
        request.user = user
        request.user.is_authenticated.return_value = True
        with patch('r3sourcer.apps.candidate.models.get_current_request', return_value=request):
            tag_rel.tag.evidence_required_for_approval = False
            tag_rel.verify = True
            tag_rel.save()
            assert tag_rel.verified_by == company_contact
            assert candidate.are_tags_verified()

    @pytest.mark.parametrize(
        ['weight', 'height', 'result'],
        [
            (50, 100, _("Over Weight")),
            (20, 100, _("Normal Weight")),
            (15, 100, _("Under Weight")),
            (None, 100, None),
            (10, None, None),
            (10, 0, None),
        ]
    )
    def test_get_bmi(self, weight, height, result):
        candidate = CandidateContact(weight=weight, height=height)
        assert candidate.get_bmi() == result

    @pytest.mark.parametrize(
        ['reliability_score', 'loyalty_score', 'result'],
        [(2, 0, 1), (0, 2, 1), (2, 2, 2), (0, 0, 0)]
    )
    def test_get_total_score(self, reliability_score, loyalty_score, result):
        candidate = CandidateContact(
            reliability_score=reliability_score,
            loyalty_score=loyalty_score
        )
        assert candidate.get_total_score() == result

    def test_get_phone_mobile(self, contact):
        candidate = CandidateContact(
            contact=contact,
            autoreceives_sms=True
        )
        assert candidate.get_phone_mobile() == '+41789272696'

    def test_get_phone_mobile_none(self, contact):
        candidate = CandidateContact(
            contact=contact,
            autoreceives_sms=False
        )
        assert candidate.get_phone_mobile() is None

    def test_get_email(self, contact):
        candidate = CandidateContact(
            contact=contact
        )
        assert candidate.get_email() == 'connor@test.test'

    @patch.object(SkillRel, 'get_valid_rate')
    def test_get_candidate_rate_for_skill(self, mock_rate, candidate, skill,
                                          skill_rel):
        mock_hourly_rate = PropertyMock(return_value=1)
        type(mock_rate.return_value).hourly_rate = mock_hourly_rate

        rate = candidate.get_candidate_rate_for_skill(skill)
        assert rate == 1

    @patch.object(SkillRel, 'get_valid_rate')
    def test_get_candidate_rate_for_skill_no_valid_rate(
            self, mock_rate, candidate, skill, skill_rel):
        mock_rate.return_value = None

        rate = candidate.get_candidate_rate_for_skill(skill)
        assert rate is None

    def test_get_candidate_rate_for_skill_no_skill(self, candidate, skill):
        rate = candidate.get_candidate_rate_for_skill(skill)
        assert rate is None

    def test_get_closest_company(self, candidate, candidate_rel, company):
        closest_company = candidate.get_closest_company()

        assert closest_company == company

    @patch('r3sourcer.apps.candidate.models.get_default_company')
    def test_get_closest_company_no_rel(self, mock_comp, candidate, company):
        mock_comp.return_value = company
        closest_company = candidate.get_closest_company()

        assert closest_company == company

    def test_is_residency_filled_false(self, candidate):
        assert not candidate.is_residency_filled()

    def test_is_residency_filled(self, candidate):
        candidate.residency = CandidateContact.RESIDENCY_STATUS_CHOICES.citizen
        assert candidate.is_residency_filled()

    def test_is_residency_filled_visa(self, candidate, visa_type, country):
        candidate.visa_type = visa_type
        candidate.visa_expiry_date = datetime.date.today()
        candidate.vevo_checked_at = datetime.date.today()
        candidate.nationality = country

        assert candidate.is_residency_filled()

    def test_notes(self, candidate, candidate_note):
        notes = candidate.notes

        assert notes.count() == 1

    def test_activities(self, candidate, candidate_activity):
        activities = candidate.activities

        assert activities.count() == 1

    def test_save_with_score_exists(self, contact, candidate_data):
        score = hr_models.CandidateScore()

        rc = CandidateContact.objects.create(
            contact=contact,
            candidate_scores=score
        )
        keys = ('height weight transportation_to_work strength language'
                ' reliability_score loyalty_score tax_file_number'
                ' super_annual_fund_name super_member_number bank_account'
                ' emergency_contact_name emergency_contact_phone'
                ' employment_classification').split()
        for key in keys:
            setattr(rc, key, candidate_data[key])

        assert hasattr(rc, 'candidate_scores')


@pytest.mark.django_db
class TestSkillRateRel:
    def test_skill_rate_rel_str(self, skill_rate_rel):
        assert str(skill_rate_rel) == str(skill_rate_rel.hourly_rate)


@pytest.mark.django_db
class TestSkillRel:
    def test_skill_rel_str(self, skill_rel):
        assert str(skill_rel) == '{}: {} ({}*)'.format(str(skill_rel.candidate_contact),
                                                       str(skill_rel.skill),
                                                       str(skill_rel.score))


@pytest.mark.django_db
class TestTagRel:
    def test_tag_rel_str(self, tag_rel):
        assert str(tag_rel) == tag_rel.tag.name

    def test_save_with_evidence(self, tag_rel):
        tag_rel.verify = True
        tag_rel.save()
        assert not tag_rel.verify
        assert tag_rel.verified_by is None

    def test_save_without_default_user(self, tag_rel):
        tag_rel.tag.evidence_required_for_approval = False
        tag_rel.verify = True
        tag_rel.save()
        assert tag_rel.verify
        assert tag_rel.verified_by is None

    def test_save_without_evidence_request_user(self, tag_rel, user):
        request = MagicMock()
        request.user = user
        request.user.is_authenticated.return_value = True
        with patch('r3sourcer.apps.candidate.models.get_current_request', return_value=request):
            tag_rel.tag.evidence_required_for_approval = False
            tag_rel.verify = True
            tag_rel.save()
            assert tag_rel.verify
            assert tag_rel.verified_by is None

    def test_save_without_evidence_company_contact_user(self, tag_rel, user, company_contact):
        request = MagicMock()
        request.user = user
        request.user.is_authenticated.return_value = True
        with patch('r3sourcer.apps.candidate.models.get_current_request', return_value=request):
            tag_rel.tag.evidence_required_for_approval = False
            tag_rel.verify = True
            tag_rel.save()
            assert tag_rel.verify
            assert tag_rel.verified_by == company_contact

    def test_verification_evidence_path(self, tag_rel):
        assert tag_rel.verification_evidence_path('filename') == \
               'candidates/tags/{}/{}'.format(tag_rel.id, 'filename')


@pytest.mark.django_db
class TestInterviewSchedule:
    def test_inverview_schedule_str(self, candidate):
        now = timezone.now()
        interview_schedule = InterviewSchedule(
            candidate_contact=candidate, target_date_and_time=now)
        assert str(interview_schedule) == "{}: {}".format(candidate, now)


@pytest.mark.django_db
class TestCandidateRel:
    def test_candidate_rel_str(self, candidate, company, company_contact):
        rr = CandidateRel.objects.create(
            candidate_contact=candidate,
            master_company=company,
            company_contact=company_contact
        )
        assert str(rr) == "{}: {}".format(company, candidate)


@pytest.mark.django_db
class TestAcceptanceTestRel:

    def test_str(self, candidate, acceptance_test):
        obj = AcceptanceTestRel(
            acceptance_test=acceptance_test,
            candidate_contact=candidate
        )
        assert str(obj) == "{} {}".format(str(candidate), str(acceptance_test))


@pytest.mark.django_db
class TestAcceptanceTestQuestionRel:

    def test_str(self, acceptance_test_rel, acceptance_question,
                 acceptance_answer):
        obj = AcceptanceTestQuestionRel(
            candidate_acceptance_test=acceptance_test_rel,
            acceptance_test_question=acceptance_question,
            acceptance_test_answer=acceptance_answer
        )

        obj_str = '{}, {}: {}'.format(str(acceptance_test_rel),
                                      str(acceptance_question),
                                      str(acceptance_answer))

        assert str(obj) == obj_str

    def test_get_if_correct(self, acceptance_test_rel, acceptance_question,
                            acceptance_answer):
        obj = AcceptanceTestQuestionRel(
            candidate_acceptance_test=acceptance_test_rel,
            acceptance_test_question=acceptance_question,
            acceptance_test_answer=acceptance_answer
        )

        assert obj.get_if_correct()


@pytest.mark.django_db
class TestSubcontractor:

    def test_str_candidate(self, candidate, company):
        sub_type = Subcontractor.SUBCONTRACTOR_TYPE_CHOICES.sole_trader
        obj = Subcontractor(
            primary_contact=candidate,
            company=company,
            subcontractor_type=sub_type
        )

        assert str(obj) == str(candidate)

    def test_str_company(self, candidate, company):
        sub_type = Subcontractor.SUBCONTRACTOR_TYPE_CHOICES.company
        obj = Subcontractor(
            primary_contact=candidate,
            company=company,
            subcontractor_type=sub_type
        )

        assert str(obj) == str(company)

    def test_str_none(self, candidate, company):
        sub_type = 'test'
        obj = Subcontractor(
            primary_contact=candidate,
            company=company,
            subcontractor_type=sub_type
        )

        assert str(obj) == str(company)
