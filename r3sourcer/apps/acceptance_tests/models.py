from django.db import models
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.models import UUIDModel
from r3sourcer.apps.skills.models import Skill


class AcceptanceTest(UUIDModel):

    test_name = models.CharField(
        max_length=255,
        verbose_name=_("Test Name")
    )

    description = models.TextField(
        verbose_name=_("Description"),
        blank=True
    )

    valid_from = models.DateField(
        verbose_name=_("Valid From")
    )

    valid_until = models.DateField(
        verbose_name=_("Valid Until")
    )

    is_active = models.BooleanField(
        verbose_name=_("Active"),
        default=False
    )

    class Meta:
        verbose_name = _("Acceptance Test")
        verbose_name_plural = _("Acceptance Tests")

    def __str__(self):
        return self.test_name


class AcceptanceTestSkill(UUIDModel):
    acceptance_test = models.ForeignKey(
        AcceptanceTest,
        on_delete=models.CASCADE,
        related_name='acceptance_tests_skills',
        verbose_name=_("Acceptance Test")
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='acceptance_tests_skills',
        verbose_name=_("Skill")
    )

    class Meta:
        verbose_name = _("Acceptance Test Skill")
        verbose_name_plural = _("Acceptance Tests and Skills")

    def __str__(self):
        return '{}, {}'.format(str(self.acceptance_test), str(self.skill))

    def get_all_questions(self):
        return self.acceptance_test.acceptance_test_questions.all()


class AcceptanceTestQuestion(UUIDModel):
    acceptance_test = models.ForeignKey(
        AcceptanceTest,
        on_delete=models.CASCADE,
        related_name='acceptance_test_questions',
        verbose_name=_("Acceptance Test")
    )

    question = models.CharField(
        max_length=255,
        verbose_name=_("Question")
    )

    details = models.TextField(
        verbose_name=_("Details"),
        blank=True
    )

    class Meta:
        verbose_name = _("Acceptance Test Question")
        verbose_name_plural = _("Acceptance Test Questions")

    def __str__(self):
        return self.question

    def get_correct_answers(self):
        return self.acceptance_test_answers.filter(is_correct=True)

    def get_all_answers(self):
        return self.acceptance_test_answers.all()


class AcceptanceTestAnswer(UUIDModel):
    acceptance_test_question = models.ForeignKey(
        AcceptanceTestQuestion,
        on_delete=models.CASCADE,
        related_name='acceptance_test_answers',
        verbose_name=_("Acceptance Test Question")
    )

    answer = models.CharField(
        max_length=255,
        verbose_name=_("Answer")
    )

    order = models.SmallIntegerField(
        verbose_name=_("Order")
    )

    is_correct = models.BooleanField(
        default=False,
        verbose_name=_("Is correct")
    )

    class Meta:
        verbose_name = _("Acceptance Test Answer")
        verbose_name_plural = _("Acceptance Test Answers")

    def __str__(self):
        return '{}: {}'.format(self.acceptance_test_question, self.answer)
