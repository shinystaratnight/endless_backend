import logging

from collections import defaultdict

from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils import timezone

from r3sourcer.apps.candidate.models import SkillRel
from r3sourcer.apps.hr.models import TimeSheet
from r3sourcer.apps.hr.payment import calc_worked_delta
from r3sourcer.apps.myob.mappers import TimeSheetMapper, format_date_to_myob
from r3sourcer.apps.myob.models import MYOBSyncObject
from r3sourcer.apps.myob.services.base import BaseSync
from r3sourcer.apps.myob.services.candidate import CandidateSync
from r3sourcer.apps.myob.services.decorators import myob_enabled_mode
from r3sourcer.apps.myob.services.mixins import BaseCategoryMixin, StandardPayMixin, CandidateCardFinderMixin
from r3sourcer.apps.pricing.models import RateCoefficientModifier
from r3sourcer.apps.pricing.services import CoefficientService


log = logging.getLogger(__name__)


def format_short_wage_category_name(skill_name, rate_name):
    return '{} {}'.format(skill_name, rate_name)[:31]


class TimeSheetSync(
    BaseCategoryMixin,
    StandardPayMixin,
    CandidateCardFinderMixin,
    BaseSync
):
    app = "crm_hr"
    model = "TimeSheet"

    mapper_class = TimeSheetMapper
    timesheet_rates_calc = None

    rates_cache = {}

    def __init__(self, myob_client=None, company=None, cf_id=None):
        super().__init__(myob_client=myob_client, company=company, cf_id=cf_id)

        self._existing_timesheets_dates = None
        self._customer_cache = {}
        self._employee_cache = {}

    @classmethod
    def from_candidate(cls, candidate):
        company = candidate.get_closest_company()
        company_settings = getattr(company, 'myob_settings', None)
        if company_settings and company_settings.timesheet_company_file:
            return cls(cf_id=company_settings.timesheet_company_file.cf_id)

        return None

    @method_decorator(myob_enabled_mode)
    def sync_to_myob(self, candidate):
        timesheets_q = (Q(candidate_submitted_at__isnull=True) | Q(candidate_submitted_at=None) |
                        Q(supervisor_approved_at__isnull=True) | Q(supervisor_approved_at=None))

        for company_file_token in self.company.company_file_tokens.all():
            enabled_qry = Q()
            if company_file_token.enable_from:
                enabled_qry |= Q(shift_started_at__date__lt=company_file_token.enable_from)
            if company_file_token.enable_until:
                enabled_qry |= Q(shift_started_at__date__gt=company_file_token.enable_until)

            # do:
            # prepare queryset for time sheet excluding not signed
            timesheet_qs = TimeSheet.objects.filter(job_offer__candidate_contact=candidate).exclude(
                timesheets_q | enabled_qry
            )
            # done;

            # exit if time sheets not found after excluding
            if not timesheet_qs.exists():
                continue

            # self._switch_client(company_file_token=company_file_token)
            self._sync_timesheets_to_myob(candidate, timesheet_qs)

    @method_decorator(myob_enabled_mode)
    def sync_single_to_myob(self, timesheet):
        timesheets_q = (Q(candidate_submitted_at__isnull=True) | Q(candidate_submitted_at=None) |
                        Q(supervisor_approved_at__isnull=True) | Q(supervisor_approved_at=None))
        timesheet_qs = TimeSheet.objects.filter(id=timesheet.id).exclude(timesheets_q)

        self._sync_timesheets_to_myob(timesheet.job_offer.candidate_contact, timesheet_qs)

    def _sync_timesheets_to_myob(self, candidate, timesheet_qs):
        if self.client is None:
            log.info('MYOB client is not defined')
            return

        # do:
        # get all synced time sheets and exclude it
        synced_timesheets = self._get_sync_objects_for_type().filter(
            record__in=timesheet_qs.values_list('id', flat=True)
        )
        timesheets_exclude = Q()
        for synced_timesheet in synced_timesheets:
            timesheets_exclude |= Q(id=synced_timesheet.record, updated_at__lte=synced_timesheet.synced_at)
        timesheets = timesheet_qs.exclude(timesheets_exclude)
        # done;

        # exit if times heets not found after excluding
        if not timesheets.exists():
            return

        # find existing remote resource
        myob_employee = self._get_myob_employee_data(candidate)

        # TODO: fix this when candidate sync will be done
        # if resource was not exists then stop processing
        if not myob_employee:
            rs = CandidateSync(self.client, self.company)
            rs.sync_to_myob(candidate, partial=True)

            myob_employee = self._get_myob_employee_data(candidate)

        if not myob_employee:
            return

        # get existing remote time sheets in date range by job id
        start_date = timezone.make_naive(timesheets.earliest('shift_started_at').shift_started_at)
        end_date = timezone.make_naive(timesheets.latest('shift_started_at').shift_started_at)
        self._existing_timesheets_dates, payroll_categories = self._get_existing_timesheets_data(
            myob_employee, start_date, end_date
        )

        is_synced = False
        for timesheet in timesheets:
            # check if company file is enabled
            cf_data = self.client.cf_data
            if not cf_data.is_enabled(timesheet.shift_started_at):
                continue

            sync_obj = self._get_sync_object(timesheet)  # type: MYOBSyncObject

            # if object was synced then skip processing
            if sync_obj and self._is_synced(timesheet, sync_obj=sync_obj):
                if timesheet.status != TimeSheet.SYNC_STATUS_CHOICES.synced:
                    timesheet.set_sync_status(TimeSheet.SYNC_STATUS_CHOICES.synced)
                continue

            timesheet.set_sync_status(TimeSheet.SYNC_STATUS_CHOICES.syncing)

            # sync time sheet
            res = self._sync_to(timesheet, myob_employee, payroll_categories, sync_obj)

            if res:
                is_synced = True
                # update sync object in local db
                self._update_sync_object(timesheet)

                timesheet.set_sync_status(TimeSheet.SYNC_STATUS_CHOICES.synced)
            else:
                timesheet.set_sync_status(TimeSheet.SYNC_STATUS_CHOICES.sync_failed)

        if is_synced:
            self._put_standart_pay_info(myob_employee, candidate)
        self._existing_timesheets_dates = None

    def _get_resource(self):
        return self.client.api.Payroll.Timesheet

    def _get_myob_employee_data(self, candidate):
        """
        Return myob candidate response if it exists in remote service.
        Find Employee card from remote resources.

        :param candidate: CandidateContact instance
        :return: dict MYOB response
        """
        # check if candidate already was cached and return value
        if self._employee_cache.get((candidate.id, self.client.cf_data.company_file.id)):
            return self._employee_cache[(candidate.id, self.client.cf_data.company_file.id)]

        # get latest sync instance for concrete candidate
        model_parts = ['hr', 'candidatecontact']
        sync_obj = MYOBSyncObject.objects.filter(
            app=model_parts[0],
            model=model_parts[1],
            record=candidate.id,
            company=self.company,
            direction=MYOBSyncObject.SYNC_DIRECTION_CHOICES.myob
        ).first()

        # find candidate resource by `DisplayID`
        _, _, myob_employee_resp = self._get_myob_existing_resp(
            candidate,
            candidate.contact.get_myob_card_number(),
            sync_obj, resource=self.client.api.Contact.Employee
        )

        myob_employee = None
        # if resource exists then return it
        if myob_employee_resp is not None and myob_employee_resp.get('Count'):
            myob_employee = myob_employee_resp['Items'][0]

        # set to cache
        if myob_employee is not None:
            self._employee_cache[(candidate.id, self.client.cf_data.company_file.id)] = myob_employee

        return myob_employee

    def _get_existing_timesheets_data(self, myob_employee, start_date, end_date):
        """
        Returns existing MYOB timesheets dates and payroll categories
        """
        params = {
            'StartDate': format_date_to_myob(start_date),
            'EndDate': format_date_to_myob(end_date),
            '$filter': "Employee/UID eq guid'{}'".format(
                myob_employee['UID']
            )
        }
        timesheet_obj = self._get_object(params, resource=self.client.api.Payroll.Timesheet, single=True)

        dates = set()
        payroll_categories = set()
        if not timesheet_obj:
            return dates, payroll_categories

        for line in timesheet_obj.get('Lines', []):
            payroll_categories.add(line['PayrollCategory']['UID'])
            for entry in line.get('Entries', []):
                dates.add(entry['Date'].split('T')[0])

        return dates, payroll_categories

    def _sync_to(self, timesheet, myob_employee, payroll_categories, sync_obj=None):
        if self.timesheet_rates_calc is None:
            self.timesheet_rates_calc = CoefficientService()

        data = self._get_timesheet_data(timesheet, myob_employee)

        # PUT times sheet data if it need
        if data is not None:
            resp = self.resource.put(uid=myob_employee['UID'], json=data, raw_resp=True)

            if resp.status_code >= 400:
                log.warning("[MYOB API] Timesheet %s: %s", timesheet.id, resp.text)

        log.info('Timesheet %s synced' % timesheet.id)
        return True

    def _get_timesheet_data(self, timesheet, myob_employee):
        """
        Return time sheet data for myob api scheme.

        :param timesheet: object TimeSheet
        :param myob_employee: dict MYOB employee
        :return: dict or None
        """

        timesheet_date = format_date_to_myob(timezone.localtime(timesheet.shift_started_at).date())

        # slip processing if time sheet date already exists in myob
        if timesheet_date in self._existing_timesheets_dates:
            return

        timesheets_with_rates = self._process_employee_timesheet_rates(timesheet)
        wage_categories = timesheets_with_rates.keys()
        self._update_employee_payroll_categories(myob_employee, wage_categories)

        data = self.mapper.map_to_myob(
            timesheets_with_rates, myob_employee['UID'], timesheet.shift_started_at, timesheet.shift_started_at
        )

        return data

    def _process_employee_timesheet_rates(self, timesheet):
        """

        :param booking: object Booking
        :param timesheet: object TimeSheet
        :return:
        """

        job = timesheet.job_offer.job
        position = job.position  # type: Position
        started_at = timezone.localtime(timesheet.shift_started_at)
        worked_hours = calc_worked_delta(timesheet)
        timesheets_with_rates = self.timesheet_rates_calc.calc(
            job.jobsite.industry,
            RateCoefficientModifier.TYPE_CHOICES.candidate,
            started_at,
            worked_hours,
            break_started=timesheet.break_started_at,
            break_ended=timesheet.break_ended_at,
        )

        result = defaultdict(dict)
        rate_myob_id, base_rate = self._get_candidate_skill_rate_and_name(timesheet)
        if not rate_myob_id:
            rate_myob_id = position.get_myob_name()

        for coeff_hours in timesheets_with_rates:
            coefficient = coeff_hours['coefficient']

            if coefficient == 'base':
                myob_rate = self._get_base_rate_wage_category(rate_myob_id, base_rate=base_rate)
            else:
                myob_rate = self._get_rate_wage_category(job, coefficient, base_rate, skill_name=rate_myob_id)

            if myob_rate:
                timesheets_rate = result[myob_rate['UID']]
                timesheets_rate['timesheets'] = [dict(
                    timesheet=timesheet,
                    **coeff_hours
                )]

        return result

    def _get_candidate_skill_rate_and_name(self, timesheet):
        offer = timesheet.job_offer
        shift = offer.shift
        name = None
        job = timesheet.job_offer.job
        skill_name = job.position.get_myob_name()
        if timesheet.rate_overrides_approved_by and timesheet.candidate_rate:
            return '{} {}'.format(
                str(skill_name),
                str(timesheet.candidate_rate)
            ), timesheet.candidate_rate
        if shift.hourly_rate:
            return '{} {}'.format(
                str(skill_name),
                str(shift.hourly_rate)
            ), shift.hourly_rate
        if shift.date.hourly_rate:
            return '{} {}'.format(
                str(skill_name),
                str(shift.date.hourly_rate)
            ), shift.date.hourly_rate
        if job.hourly_rate_default:
            name = '{} {}'.format(
                str(job.position.get_myob_name()),
                str(job.hourly_rate_default)
            )
            base_rate = job.hourly_rate_default

        if name is None:
            candidate_skill_rate = SkillRel.objects.filter(
                candidate_contact=offer.candidate_contact,
                skill__active=True,
                skill=job.position,
            ).first()
            name = candidate_skill_rate and candidate_skill_rate.get_myob_name()
            base_rate = candidate_skill_rate.hourly_rate if candidate_skill_rate else 0
        return name, base_rate

    def _get_base_rate_wage_category(self, name, rate=None, base_rate=None):
        myob_wage_category = self._get_object_by_field(
            name[:31].strip().lower(),
            resource=self.client.api.Payroll.PayrollCategory.Wage,
            myob_field='tolower(Name)',
            single=True
        )

        if rate:
            fixed = rate.candidate_modifier.calc(base_rate) if rate.candidate_modifier else 0
            if fixed <= 0:
                return

            data = self.mapper.map_rate_to_myob_wage_category(name, fixed=fixed)
        elif base_rate:
            data = self.mapper.map_rate_to_myob_wage_category(name, fixed=base_rate)
        elif myob_wage_category is None:
            return
        else:
            data = myob_wage_category

        # create wage if category was not found from remote or update it by ID
        if myob_wage_category is None:
            resp = self.client.api.Payroll.PayrollCategory.Wage.post(json=data, raw_resp=True)
        else:
            data['UID'] = myob_wage_category['UID']
            data['RowVersion'] = myob_wage_category['RowVersion']
            resp = self.client.api.Payroll.PayrollCategory.Wage.put(
                uid=myob_wage_category['UID'], json=data, raw_resp=True
            )

        if resp.status_code >= 400:
            log.warning(resp.text)
        elif myob_wage_category is None:
            myob_wage_category = self._get_object_by_field(
                name[:31].strip().lower(),
                resource=self.client.api.Payroll.PayrollCategory.Wage,
                myob_field='tolower(Name)',
                single=True
            )

        return myob_wage_category

    def _get_rate_wage_category(self, job, rate, base_rate, name=None, skill_name=''):
        if rate.is_allowance:
            industry = job.jobsite.industry
            name = '{} {}'.format(''.join([line[0] for line in industry.type.split(' ')]), rate.name)
        if not name:
            name = format_short_wage_category_name(skill_name, rate.name)
        return self._get_base_rate_wage_category(name[:31].strip(), rate=rate, base_rate=base_rate)

    def _update_employee_payroll_categories(self, employee, categories):
        uid = employee['EmployeePayrollDetails']['UID']
        payroll_details = self.client.api.Contact.EmployeePayrollDetails.get(uid=uid) or {}
        wage = payroll_details.get('Wage', {})

        if self._employee_has_wage_categories(wage.get('WageCategories'), categories):
            return

        data_categories = self.mapper.map_extra_rates(categories, rates=wage.get('WageCategories'))
        wage.update(data_categories)
        payroll_details['Wage'] = wage
        resp = self.client.api.Contact.EmployeePayrollDetails.put(uid=uid, json=payroll_details, raw_resp=True)

        if resp.status_code >= 400:
            log.warning("[MYOB API] payroll details for myob %s: %s", uid, resp.text)
        else:
            log.info('payroll details for myob %s updated' % uid)

    def _employee_has_wage_categories(self, existing_categories, new_categories):
        existing_categories = existing_categories or []
        new_categories = new_categories or []
        found_cnt = 0
        for category_uid in new_categories:
            for existing in existing_categories:
                if existing['UID'] == category_uid:
                    found_cnt += 1
                    break
        return found_cnt == len(new_categories)
