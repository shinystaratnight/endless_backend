import pytest

from r3sourcer.apps.hr.api.serializers.timesheet import TimeSheetSerializer


class TestTimeSheetSerializer:

    @pytest.fixture
    def serializer(self):
        return TimeSheetSerializer()

    def test_get_company(self, serializer, timesheet, master_company):
        res = serializer.get_company(timesheet)

        assert res == str(master_company)

    def test_get_company_none(self, serializer, timesheet):
        res = serializer.get_company(None)

        assert res is None

    def test_get_jobsite(self, serializer, timesheet, jobsite):
        res = serializer.get_jobsite(timesheet)

        assert res == str(jobsite)

    def test_get_jobsite_none(self, serializer, timesheet):
        res = serializer.get_jobsite(None)

        assert res is None

    def test_get_position(self, serializer, timesheet, skill):
        res = serializer.get_position(timesheet)

        assert res == str(skill)

    def test_get_position_none(self, serializer, timesheet):
        res = serializer.get_position(None)

        assert res is None
