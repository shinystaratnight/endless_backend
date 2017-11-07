import pytest


@pytest.mark.django_db
class TestAcceptanceTest:
    def test_str(self, acceptance_test):
        assert str(acceptance_test) == acceptance_test.test_name


@pytest.mark.django_db
class TestAcceptanceTestSkill:
    def test_str(self, acceptance_test_skill):
        assert str(acceptance_test_skill) == "{}, {}".\
            format(str(acceptance_test_skill.acceptance_test),
                   str(acceptance_test_skill.skill))

    def test_get_all_questions_with_result(self, acceptance_test_skill,
                                           answer):
        assert acceptance_test_skill.get_all_questions().count() == 1


@pytest.mark.django_db
class TestAcceptanceTestQuestion:
    def test_str(self, question):
        assert str(question) == question.question

    def test_get_correct_answers(self, question, answer):
        assert question.get_correct_answers().count() == 1

    def test_get_all_answers(self, question, answer, answer_wrong):
        assert question.get_all_answers().count() == 2


@pytest.mark.django_db
class TestAcceptanceTestAnswer:
    def test_str(self, answer):
        assert str(answer) == 'question: answer'
