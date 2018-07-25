import datetime
import pytest

from r3sourcer.apps.acceptance_tests import models
from r3sourcer.apps.core.models import WorkflowNode
from r3sourcer.apps.hr.models import Skill


@pytest.fixture
def skill(db):
    return Skill.objects.create(
        name="Driver",
        carrier_list_reserve=2,
        short_name="Drv",
        active=False
    )


@pytest.fixture
def acceptance_test(db):
    return models.AcceptanceTest.objects.create(
        test_name='test',
        valid_from=datetime.date(2017, 1, 1),
        valid_until=datetime.date(2018, 1, 1),
        is_active=True
    )


@pytest.fixture
def question(db, acceptance_test):
    return models.AcceptanceTestQuestion.objects.create(
        acceptance_test=acceptance_test,
        question='question',
        order=1
    )


@pytest.fixture
def answer(db, question):
    return models.AcceptanceTestAnswer.objects.create(
        acceptance_test_question=question,
        answer='answer',
        order=0,
        is_correct=True
    )


@pytest.fixture
def answer_wrong(db, question):
    return models.AcceptanceTestAnswer.objects.create(
        acceptance_test_question=question,
        answer='answer wrong',
        order=0,
        is_correct=False
    )


@pytest.fixture
def acceptance_test_skill(db, acceptance_test, skill):
    return models.AcceptanceTestSkill.objects.create(
        acceptance_test=acceptance_test,
        skill=skill
    )
