from django.db.models import Manager, Sum, Case, When, IntegerField, F, Q

from r3sourcer.apps.hr.models import JobOffer


class SelectRelatedSkillManager(Manager):
    def get_queryset(self):
        return super(SelectRelatedSkillManager, self).get_queryset().select_related('skill')


class SkillManager(Manager):

    def filtered_for_carrier_list(self, target_date_and_time):
        """Filters skill list
        Checks every skill and counts how many candidates we have on carrier list for that skill on Target date.
        Conditions:
            Is on carrier list for Target date
            JobOffer for that date is not accepted
            Carrier list confirmed available for Target date
        Filter skills from the list. Conditions:
            Skill must be active
            Carrier list count is less than Carrier list reserve"""
        return self.get_queryset().annotate(carrier_list_count=Sum(Case(
            When(
                Q(candidate_skills__candidate_contact__carrier_lists__target_date=target_date_and_time.date()) &
                Q(candidate_skills__candidate_contact__carrier_lists__confirmed_available=True) &
                ~Q(candidate_skills__candidate_contact__carrier_lists__job_offer__status=JobOffer.STATUS_CHOICES.accepted),
                then=1),
            output_field=IntegerField(),
            default=0))
        ).filter(
            active=True,
            carrier_list_count__lt=F('carrier_list_reserve')
            # carrier_list_count__lt=F('carrier_list_reserve') / 2 if is_saturday else F('carrier_list_reserve')
        )
