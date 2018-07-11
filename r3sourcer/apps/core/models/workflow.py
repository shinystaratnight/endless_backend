from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.models.core import UUIDModel, Company
from r3sourcer.apps.core.utils.companies import get_site_master_company


__all__ = [
    'Workflow',
    'WorkflowNode',
    'WorkflowObject',
]


class Workflow(UUIDModel):
    name = models.CharField(
        verbose_name=_('Name'),
        max_length=64
    )

    model = models.ForeignKey(
        ContentType,
        verbose_name=_('Binding model')
    )

    class Meta:
        verbose_name = _('Workflow')
        verbose_name_plural = _('Workflows')

    def __str__(self):
        return self.name

    @classmethod
    def is_owned(cls):
        return False


class WorkflowNode(UUIDModel):
    workflow = models.ForeignKey(
        Workflow,
        related_name='nodes',
        on_delete=models.PROTECT,
        verbose_name=_('Workflow')
    )

    number = models.PositiveSmallIntegerField(
        verbose_name=_('State number')
    )

    full_path = models.CharField(
        max_length=32,
        editable=False,
        verbose_name=_('Full path')
    )

    name_before_activation = models.CharField(
        verbose_name=_('State name before activation'),
        max_length=128
    )

    name_after_activation = models.CharField(
        verbose_name=_('State name after activation'),
        max_length=128,
        null=True,
        blank=True
    )

    active = models.BooleanField(
        verbose_name=_('Active'),
        default=True
    )

    rules = JSONField(
        verbose_name=_('Rules'),
        null=True,
        blank=True
    )

    company = models.ForeignKey(
        Company,
        related_name='company_wf_nodes',
        on_delete=models.PROTECT,
        verbose_name=_('Company')
    )

    hardlock = models.BooleanField(
        verbose_name=_('Hardlock'),
        default=False
    )

    endpoint = models.CharField(
        verbose_name=_('Endpoint to activate state'),
        max_length=255,
        null=True,
        blank=True
    )

    initial = models.BooleanField(
        verbose_name=_('Is initial state'),
        default=False
    )

    parent = models.ForeignKey(
        'self',
        verbose_name=_('Parent Node'),
        null=True,
        blank=True,
        related_name='children'
    )

    class Meta:
        verbose_name = _('Workflow Node')
        verbose_name_plural = _('Workflow Nodes')
        unique_together = ('company', 'number', 'workflow')

    def __str__(self):
        return '{} {}, {}, {}'.format(self.full_path, self.workflow, self.name_before_activation, self.company)

    def save(self, *args, **kwargs):
        if not self.company:
            self.company = get_site_master_company()

        self.full_path = self.get_full_number()
        super().save(*args, **kwargs)

    def clean(self):
        self.validate_node(
            self.number, self.workflow, self.company, self.active, self.rules,
            self._state.adding, self.id or None
        )

    @classmethod
    def validate_node(cls, number, workflow, company, active,
                      rules, just_added, _id=None):
        system_company = get_site_master_company()
        system_node = None
        if company != system_company:
            system_node = WorkflowNode.objects.filter(
                company=system_company,
                workflow=workflow,
                number=number
            ).first()

            if system_node and system_node.hardlock:
                if active != system_node.active:
                    raise ValidationError(
                        _('Active for system node cannot be changed.')
                    )
                elif rules != system_node.rules:
                    raise ValidationError(
                        _('Rules for system node cannot be changed.')
                    )

        if not just_added:
            origin = WorkflowNode.objects.get(id=_id)
            number_changed = origin.number != number

            if company != system_company and system_node \
                    and system_node.hardlock and number_changed:
                raise ValidationError(
                    _('Number for system node cannot be changed.')
                )

            if number_changed:
                nodes = WorkflowNode.objects.filter(
                    company=company, workflow=workflow
                )
                is_used = [
                    node.rules and str(origin.number) in node.get_rule_states()
                    for node in nodes
                ]
                if any(is_used):
                    raise ValidationError(
                        _("Number is used in other node's rules.")
                    )

    def get_rule_states(self):
        if self.rules and 'required_states' in self.rules:
            rule = self.rules['required_states']
            return str(self._get_state_from_rule(rule))\
                .replace('[', '').replace(']', '').replace(' ', '').split(',')
        return ''

    def _get_state_from_rule(self, rule):
        if isinstance(rule, list):
            return self._get_state_from_list(rule[1:])
        elif isinstance(rule, int):
            return rule

    def _get_state_from_list(self, rules):
        return [self._get_state_from_rule(rule) for rule in rules]

    @classmethod
    def get_company_nodes(cls, company, workflow=None, nodes=None):
        default_company = get_site_master_company()

        queryset = nodes or cls.objects

        qry = models.Q(company=company, active=True)
        default_qry = models.Q(company=default_company, active=True)
        if workflow is not None:
            qry &= models.Q(workflow=workflow)
            default_qry &= models.Q(workflow=workflow)

        if default_company != company:
            company_numbers = list(
                queryset.filter(qry).values_list('number', flat=True)
            )
        else:
            company_numbers = []

        company_nodes = queryset.filter(
            qry | default_qry
        ).exclude(
            models.Q(number__in=company_numbers) & default_qry
        ).order_by('number')

        return company_nodes

    @classmethod
    def get_model_all_states(cls, model):
        states = cls.objects.filter(
            workflow__model=ContentType.objects.get_for_model(model)
        ).distinct('number').values(
            'number', 'name_before_activation', 'name_after_activation'
        )

        return [
            {'label': s['name_after_activation'] or s['name_before_activation'], 'value': s['number']} for s in states
        ]

    @classmethod
    def is_owned(cls):
        return False

    def get_full_number(self):
        if self.full_path is not None:
            return self.full_path

        if self.parent is None:
            return self.number

        return '{}.{}'.format(self.parent.full_path, self.number)


class WorkflowObject(UUIDModel):
    object_id = models.UUIDField(
        verbose_name=_('Object id'),
        help_text=_('ID of Object belonging to model in Workflow')
    )

    state = models.ForeignKey(
        WorkflowNode,
        verbose_name=_('State'),
        related_name='states'
    )

    comment = models.TextField(
        verbose_name=_('Comments'),
        help_text=_('State Change Comment'),
        blank=True
    )

    active = models.BooleanField(
        verbose_name=_('Active'),
        default=True
    )

    score = models.SmallIntegerField(
        verbose_name=_('State score'),
        default=0
    )

    class Meta:
        verbose_name = _('Workflow object')
        verbose_name_plural = _('Workflow objects')

    def __str__(self):
        return str(self.state)

    @property
    def model_object(self):
        return self.get_model_object(self.state, self.object_id)

    @classmethod
    def get_model_object(cls, state, object_id):
        result = None
        model = state.workflow.model.model_class()
        try:
            result = model.objects.get(id=object_id)
        except Exception:
            pass
        return result

    def save(self, *args, **kwargs):
        is_raw = kwargs.pop('raw', False)
        if not is_raw:
            self.clean()

        just_added = self._state.adding

        lifecycle_enabled = kwargs.pop('lifecycle', True)

        if just_added and lifecycle_enabled:
            self.model_object.before_state_creation(self)

        super().save(*args, **kwargs)

        if just_added:
            if not is_raw:
                self.model_object.workflow(self.state)

            if lifecycle_enabled:
                self.model_object.after_state_created(self)

    def clean(self):
        self.validate_object(self.state, self.object_id, self._state.adding)

    @classmethod
    def validate_object(cls, state, object_id, just_added):
        model = state.workflow.model.model_class()
        try:
            model.objects.get(id=object_id)
        except Exception as e:
            raise ValidationError(e)

        model_object = cls.get_model_object(state, object_id)
        if state.company != model_object.get_closest_company() \
                and state.company != get_site_master_company():
            raise ValidationError(
                _('This state is not available for current object.')
            )

        if just_added and not model_object.is_allowed(state):
            raise ValidationError('{} {}'.format(
                _('State creation is not allowed.'),
                model_object.get_required_message(state))
            )
