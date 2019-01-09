from datetime import datetime

import freezegun
import pytest

from pytz import timezone

from django.conf import settings as dj_settings

from r3sourcer.apps.hr.api.serializers.timesheet import TimeSheetSerializer
from r3sourcer.apps.hr.api.serializers.job import JobSerializer


tz = timezone(dj_settings.TIME_ZONE)


class TestTimeSheetSerializer:

    @pytest.fixture
    def serializer(self):
        return TimeSheetSerializer()

    def test_get_company(self, serializer, timesheet, regular_company):
        res = serializer.get_company(timesheet)

        assert res == {'id': regular_company.id, '__str__': str(regular_company)}

    def test_get_company_none(self, serializer, timesheet):
        res = serializer.get_company(None)

        assert res is None

    def test_get_jobsite(self, serializer, timesheet, jobsite):
        res = serializer.get_jobsite(timesheet)

        assert res == {
            'id': jobsite.id,
            'address': {
                'id': jobsite.address.id,
                '__str__': str(jobsite.address),
            },
            '__str__': str(jobsite),
        }

    def test_get_jobsite_none(self, serializer, timesheet):
        res = serializer.get_jobsite(None)

        assert res is None

    def test_get_position(self, serializer, timesheet, skill):
        res = serializer.get_position(timesheet)

        assert res == {'id': skill.id, '__str__': str(skill)}

    def test_get_position_none(self, serializer, timesheet):
        res = serializer.get_position(None)

        assert res is None


@pytest.mark.django_db
class TestJobSerializer:

    @pytest.fixture
    def serializer(self):
        return JobSerializer()

    @freezegun.freeze_time(tz.localize(datetime(2017, 1, 1, 7)))
    def test_get_todays_timesheets(self, timesheet, job, serializer):
        res = serializer.get_todays_timesheets(job)

        assert res == '0% / 0% / 0%'

    def test_get_todays_timesheets_no_timesheet(self, job, serializer):
        res = serializer.get_todays_timesheets(job)

        assert res == '-'
