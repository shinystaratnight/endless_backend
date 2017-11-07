import datetime

import pytest
from freezegun import freeze_time
from mock import patch, PropertyMock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils.formats import date_format
from django.utils.timezone import localtime, make_aware
from django_mock_queries.query import MockSet, MockModel

from r3sourcer.apps.hr.models import (
    TimeSheet, JobsiteUnavailability, CandidateEvaluation, VacancyOffer,
    VacancyDate, TimeSheetIssue, BlackList, FavouriteList,
    NOT_FULFILLED, FULFILLED, LIKELY_FULFILLED, IRRELEVANT
)
from r3sourcer.apps.hr.utils.utils import tomorrow


@pytest.mark.django_db
class TestJobsite:
    def test_get_site_name_without_address(self, jobsite):
        assert jobsite.get_site_name() == str(jobsite.master_company)

    def test_get_site_name_with_address(self, jobsite, jobsite_address):
        street_address = jobsite_address.address.street_address
        assert street_address in jobsite.get_site_name()

    def test_get_availability_successful(self, jobsite):
        JobsiteUnavailability.objects.create(
            jobsite=jobsite,
            unavailable_from=datetime.date.today() + datetime.timedelta(days=4)
        )
        assert jobsite.get_availability() == jobsite.is_available
        assert jobsite.get_availability()

    def test_get_availability_unsuccessful(self, jobsite):
        today = datetime.date.today()
        JobsiteUnavailability.objects.create(
            jobsite=jobsite,
            unavailable_from=today,
            unavailable_until=today + datetime.timedelta(days=2)
        )
        assert not jobsite.get_availability()

    def test_get_duration(self, jobsite):
        assert jobsite.get_duration() == datetime.timedelta(7)

    def test_is_address_set_successful(self, jobsite, jobsite_address):
        assert jobsite.is_address_set()

    def test_is_address_set_unsuccessful(self, jobsite):
        assert not jobsite.is_address_set()

    def test_get_address_none(self, jobsite):
        assert jobsite.get_address() is None

    def test_get_address_with_result(self, jobsite, jobsite_address):
        assert jobsite.get_address() == jobsite_address.address

    def test_is_supervisor_set_true(self, jobsite):
        assert jobsite.is_supervisor_set()

    def test_is_supervisor_set_false(self, jobsite):
        jobsite.primary_contact = None
        assert not jobsite.is_supervisor_set()

    @freeze_time(datetime.datetime(2017, 1, 1))
    def test_save_not_changed_primary_contact(self, jobsite, vacancy_offer,
                                              company_contact,
                                              timesheet_tomorrow):
        jobsite.save()

        ts = TimeSheet.objects.filter(
            vacancy_offer__in=[vacancy_offer],
            shift_started_at__date__gte=tomorrow()
        ).first()

        assert ts.supervisor == company_contact

    @freeze_time(datetime.datetime(2017, 1, 1))
    def test_save_changed_primary_contact(self, jobsite, vacancy_offer,
                                          company_contact_another,
                                          timesheet_tomorrow):
        jobsite.primary_contact = company_contact_another
        jobsite.save()

        ts = TimeSheet.objects.filter(
            vacancy_offer__in=[vacancy_offer],
            shift_started_at__date__gte=tomorrow()
        ).first()

        assert ts.supervisor == company_contact_another

    def test_get_closest_company(self, jobsite, master_company):
        assert jobsite.get_closest_company() == master_company


@pytest.mark.django_db
class TestVacancy:
    def test_get_title(self, vacancy, jobsite, skill):
        assert str(jobsite) in str(vacancy)
        assert str(skill) in str(vacancy)
        assert str(vacancy.workers) in str(vacancy)

    def test_get_vacancy_offers(self, vacancy, vacancy_offer):
        assert vacancy.get_vacancy_offers().count() == 1

    def test_get_total_bookings_count(self, vacancy, vacancy_offer):
        assert vacancy.get_total_bookings_count() == 1

    @freeze_time(datetime.datetime(2017, 1, 2))
    def test_is_fulfilled_irrelevant(self, vacancy, vacancy_date):
        assert vacancy.is_fulfilled() == IRRELEVANT

    @freeze_time(datetime.datetime(2017, 1, 1))
    @patch.object(VacancyDate, 'is_fulfilled', return_value=FULFILLED)
    def test_is_fulfilled_fulfilled(self, mock_vd_fulfilled, vacancy,
                                    vacancy_date):
        assert vacancy.is_fulfilled() == FULFILLED

    @freeze_time(datetime.datetime(2017, 1, 1))
    @patch.object(VacancyDate, 'is_fulfilled', return_value=LIKELY_FULFILLED)
    def test_is_fulfilled_vd_likely_fulfilled(self, mock_vd_fulfilled, vacancy,
                                              vacancy_date):
        assert vacancy.is_fulfilled() == LIKELY_FULFILLED

    @freeze_time(datetime.datetime(2017, 1, 1))
    @patch.object(VacancyDate, 'is_fulfilled', return_value=IRRELEVANT)
    def test_is_fulfilled_vd_irrelevant(self, mock_vd_fulfilled, vacancy,
                                        vacancy_date):
        assert vacancy.is_fulfilled() == IRRELEVANT

    @freeze_time(datetime.datetime(2017, 1, 1))
    @patch.object(VacancyDate, 'is_fulfilled', return_value=NOT_FULFILLED)
    @patch.object(VacancyDate, 'vacancy_offers', new_callable=PropertyMock)
    def test_is_fulfilled_vd_not_fulfilled_vo_not_exists(
            self, mock_vos, mock_vd_fulfilled, vacancy, vacancy_date):
        mock_vos.return_value.exists.return_value = False

        assert vacancy.is_fulfilled() == NOT_FULFILLED

    @freeze_time(datetime.datetime(2017, 1, 1))
    @patch.object(VacancyDate, 'is_fulfilled', return_value=NOT_FULFILLED)
    @patch.object(VacancyDate, 'vacancy_offers', new_callable=PropertyMock)
    def test_is_fulfilled_vd_not_fulfilled_no_unaccepted_vos(
            self, mock_vos, mock_vd_fulfilled, vacancy, vacancy_date):
        mock_vos.return_value = MockSet(
            MockModel(status=VacancyOffer.STATUS_CHOICES.accepted)
        )

        assert vacancy.is_fulfilled() == LIKELY_FULFILLED

    @freeze_time(datetime.datetime(2017, 1, 1))
    @patch.object(VacancyDate, 'is_fulfilled', return_value=NOT_FULFILLED)
    def test_is_fulfilled_vd_not_fulfilled_accepted_ts(
            self, mock_vd_fulfilled, vacancy, vacancy_offer, vacancy_date):
        TimeSheet.objects.create(
            vacancy_offer=vacancy_offer,
            going_to_work_confirmation=True
        )

        assert vacancy.is_fulfilled() == LIKELY_FULFILLED

    @freeze_time(datetime.datetime(2017, 1, 1))
    @patch.object(VacancyDate, 'is_fulfilled', return_value=NOT_FULFILLED)
    def test_is_fulfilled_vd_not_fulfilled_no_accepted_ts(
            self, mock_vd_fulfilled, vacancy, vacancy_date, timesheet):

        assert vacancy.is_fulfilled() == NOT_FULFILLED


@pytest.mark.django_db
class TestVacancyDate:
    def test_str(self, vacancy_date):
        assert str(vacancy_date) == '{}, {}: {}'.format(date_format(
            vacancy_date.shift_date, settings.DATE_FORMAT),
            "workers", vacancy_date.workers
        )

    def test_vacancy_offers(self, vacancy_date, vacancy_offer):
        assert vacancy_date.vacancy_offers.count() == 1
        assert vacancy_offer in vacancy_date.vacancy_offers

    def test_is_fulfilled(self, vacancy_date):
        assert vacancy_date.is_fulfilled() == NOT_FULFILLED

    def test_is_fulfilled_true(self, vacancy_date, shift, candidate_contact):
        VacancyOffer.objects.create(
            shift=shift,
            candidate_contact=candidate_contact,
            status=VacancyOffer.STATUS_CHOICES.accepted,
        )
        vacancy_date.workers = 1

        assert vacancy_date.is_fulfilled() == FULFILLED


@pytest.mark.django_db
class TestShift:
    def test_str(self, shift):
        assert str(shift) == date_format(
            datetime.datetime.combine(shift.date.shift_date, shift.time),
            settings.DATETIME_FORMAT
        )

    def test_get_vacancy(self, shift, vacancy):
        assert shift.vacancy == vacancy


@pytest.mark.django_db
class TestTimesheet:

    def test_str(self, timesheet):
        assert str(timesheet) == '01/01/2017 07:00 AM  '

    def test_str_candidate_submitted(self, timesheet):
        timesheet.candidate_submitted_at = make_aware(
            datetime.datetime(2017, 1, 1, 18, 0)
        )
        assert str(timesheet) == '01/01/2017 07:00 AM 01/01/2017 06:00 PM '

    def test_str_supervisor_approved(self, timesheet):
        timesheet.candidate_submitted_at = make_aware(
            datetime.datetime(2017, 1, 1, 18, 0)
        )
        timesheet.supervisor_approved_at = make_aware(
            datetime.datetime(2017, 1, 1, 20, 0)
        )
        res = '01/01/2017 07:00 AM 01/01/2017 06:00 PM 01/01/2017 08:00 PM'
        assert str(timesheet) == res

    def test_get_vacancy_offer(self, timesheet, vacancy_offer):
        assert timesheet.get_vacancy_offer() == vacancy_offer

    def test_get_or_create_for_vacancy_offer_accepted(
            self, vacancy_offer_tomorrow):

        res = TimeSheet.get_or_create_for_vacancy_offer_accepted(
            vacancy_offer_tomorrow
        )
        assert res.vacancy_offer == vacancy_offer_tomorrow

    @patch.object(TimeSheet, 'objects', new_callable=PropertyMock)
    def test_get_or_create_for_vacancy_offer_accepted_exists(
            self, mock_objects, vacancy_offer):

        mock_objects.return_value.get_or_create.side_effect = IntegrityError
        mock_objects.return_value.update_or_create.return_value = (
            MockModel(vacancy_offer=vacancy_offer), True
        )

        res = TimeSheet.get_or_create_for_vacancy_offer_accepted(vacancy_offer)
        assert res.vacancy_offer == vacancy_offer

    def test_get_closest_company(self, timesheet, master_company):
        assert timesheet.get_closest_company() == master_company

    @patch.object(TimeSheet, 'create_state')
    def test_save_just_added(self, mock_create, vacancy_offer,
                             company_contact):
        TimeSheet.objects.create(
            vacancy_offer=vacancy_offer,
            supervisor=company_contact
        )

        assert mock_create.called

    @patch.object(TimeSheet, 'create_state')
    def test_save_not_just_added(self, mock_create, timesheet):
        timesheet.save()

        assert not mock_create.called

    def test_supervisor_signature_path(self, timesheet):
        res = timesheet.supervisor_signature_path('test.sig')

        assert res == 'timesheets/signature/{}.sig'.format(timesheet.id)


@pytest.mark.django_db
class TestVacancyOffer:
    def test_str(self, vacancy_offer):
        assert str(vacancy_offer) == date_format(
            localtime(vacancy_offer.created_at), settings.DATETIME_FORMAT)

    def test_get_vacancy(self, vacancy_offer, vacancy):
        assert vacancy_offer.vacancy == vacancy

    @pytest.mark.parametrize('vo,expected', [
        (VacancyOffer(status=VacancyOffer.STATUS_CHOICES.accepted), True),
        (VacancyOffer(status=VacancyOffer.STATUS_CHOICES.cancelled), False),
        (VacancyOffer(status=VacancyOffer.STATUS_CHOICES.undefined), False)
    ])
    def test_is_accepted(self, vo, expected):
        assert vo.is_accepted() == expected

    def test_is_first(self, vacancy_offer):
        assert vacancy_offer.is_first()

    def test_is_first_false(self, vacancy_offer_yesterday, vacancy_offer):
        assert not vacancy_offer.is_first()

    def test_is_recurring(self, vacancy_offer_yesterday, vacancy_offer):
        assert vacancy_offer.is_recurring()

    def test_is_recurring_false(self, vacancy_offer):
        assert not vacancy_offer.is_recurring()

    def test_get_future_offers(self, vacancy_offer_tomorrow, vacancy_offer):

        assert vacancy_offer.get_future_offers().count() == 1
        assert not vacancy_offer.is_recurring()

    def test_get_future_offers_no_offers(self, vacancy_offer):
        assert vacancy_offer.get_future_offers().count() == 0

    def test_start_time(self, vacancy_offer):
        res = make_aware(datetime.datetime(2017, 1, 2, 8, 30))
        assert vacancy_offer.start_time == res


class TestTimeSheetIssue:

    def test_str(self, timesheet):
        timesheet_issue = TimeSheetIssue(time_sheet=timesheet, subject='test')
        assert str(timesheet_issue) == '01/01/2017 07:00 AM  : test'

    def test_get_closest_company(self, timesheet_issue, master_company):
        assert timesheet_issue.get_closest_company() == master_company


@pytest.mark.django_db
class TestCarrierList:

    def test_str(self, carrier_list, candidate_contact):
        assert str(carrier_list) == '{}: {}'.format(
            candidate_contact,
            date_format(carrier_list.target_date, settings.DATE_FORMAT)
        )

    def test_confirm(self, carrier_list):
        assert not carrier_list.confirmed_available
        carrier_list.confirm()
        assert carrier_list.confirmed_available

    def test_deny(self, carrier_list):
        carrier_list.confirmed_available = True
        assert carrier_list.confirmed_available
        carrier_list.deny()
        assert not carrier_list.confirmed_available


@pytest.mark.django_db
class TestCandidateEvaluation:
    @pytest.mark.parametrize('evaluation,expected', [
        (CandidateEvaluation(was_on_time=True), 0.5),
        (CandidateEvaluation(was_on_time=True, level_of_communication=1), 1),
        (CandidateEvaluation(was_on_time=True, level_of_communication=2), 1.5),
        (CandidateEvaluation(was_on_time=True, level_of_communication=3), 2),
        (CandidateEvaluation(was_on_time=True, level_of_communication=4), 2.5),
        (CandidateEvaluation(was_on_time=True, level_of_communication=5), 3),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True), 1),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             level_of_communication=1), 1.5),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             level_of_communication=5), 3.5),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             was_motivated=True), 1.5),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             was_motivated=True, met_expectations=True), 2),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             was_motivated=True, met_expectations=True,
                             representation=True), 2.5),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             was_motivated=True, met_expectations=True,
                             representation=True,
                             level_of_communication=5), 5),
        (CandidateEvaluation(level_of_communication=5), 0),
        (CandidateEvaluation(level_of_communication=0), 0),
    ])
    def test_get_rating(self, evaluation, expected):
        assert evaluation.get_rating() == expected

    @pytest.mark.parametrize('evaluation,expected', [
        (CandidateEvaluation(was_on_time=True), 0.5),
        (CandidateEvaluation(was_on_time=True, level_of_communication=1), 1),
        (CandidateEvaluation(was_on_time=True, level_of_communication=2), 1.5),
        (CandidateEvaluation(was_on_time=True, level_of_communication=3), 2),
        (CandidateEvaluation(was_on_time=True, level_of_communication=4), 2.5),
        (CandidateEvaluation(was_on_time=True, level_of_communication=5), 3),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True), 1),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             level_of_communication=1), 1.5),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             level_of_communication=5), 3.5),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             was_motivated=True), 1.5),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             was_motivated=True, met_expectations=True), 2),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             was_motivated=True, met_expectations=True,
                             representation=True), 2.5),
        (CandidateEvaluation(was_on_time=True, had_ppe_and_tickets=True,
                             was_motivated=True, met_expectations=True,
                             representation=True,
                             level_of_communication=5), 5),
        (CandidateEvaluation(level_of_communication=5), 2.5),
        (CandidateEvaluation(level_of_communication=0), 0),
    ])
    def test_single_evaluation_average(self, evaluation, expected):
        assert evaluation.single_evaluation_average() == expected


@pytest.mark.django_db
class TestBlackList:

    def test_str(self, black_list, master_company, candidate_contact):
        assert str(black_list) == '{}: {}'.format(master_company, candidate_contact)

    def test_save_set_jobsite(self, black_list, timesheet, jobsite,
                              company_contact):
        black_list.timesheet = timesheet
        black_list.company_contact = company_contact
        black_list.clean()
        black_list.save()

        assert black_list.jobsite == jobsite

    def test_save_set_supervisor(self, black_list, timesheet, jobsite,
                                 company_contact):
        black_list.timesheet = timesheet
        black_list.jobsite = jobsite
        black_list.clean()
        black_list.save()

        assert black_list.company_contact == company_contact

    @patch.object(BlackList, 'objects', new_callable=PropertyMock)
    def test_clean(self, mock_objects, black_list):
        mock_objects.return_value.filter.return_value = MockSet(MockModel())

        with pytest.raises(ValidationError):
            black_list.clean()


@pytest.mark.django_db
class TestFavouriteList:

    def test_str(self, favourite_list, company_contact, candidate_contact):
        assert str(favourite_list) == '{}: {}'.format(company_contact, candidate_contact)

    def test_save_set_company(self, favourite_list, jobsite, master_company):
        favourite_list.jobsite = jobsite
        favourite_list.clean()
        favourite_list.save()

        assert favourite_list.company == master_company

    def test_save_set_jobsite(self, favourite_list, vacancy, jobsite, master_company):
        favourite_list.vacancy = vacancy
        favourite_list.clean()
        favourite_list.save()

        assert favourite_list.jobsite == jobsite
        assert favourite_list.company == master_company

    @patch.object(FavouriteList, 'objects', new_callable=PropertyMock)
    def test_clean(self, mock_objects, favourite_list):
        mock_objects.return_value.filter.return_value = MockSet(MockModel())

        with pytest.raises(ValidationError):
            favourite_list.clean()
