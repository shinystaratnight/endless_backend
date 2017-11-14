from datetime import date
from functools import reduce

from django.db import models
from django.db.models import Q
from mptt.managers import TreeManager


class TagManager(TreeManager):
    def active(self):
        return self.get_queryset().filter(active=True)


class AbstractObjectOwnerManager(models.Manager):
    passed_models = []

    def owned_by(self, _obj):
        lookups = self.get_lookups(_obj)

        if not lookups:
            lookups = self._get_obj_related_lookups(_obj)

        if lookups:
            from operator import __or__ as OR
            return super().get_queryset().filter(reduce(OR, lookups)).distinct()
        return super().get_queryset().none()

    def get_lookups(self, _obj, path=''):
        path_list = []

        related_fields = [
            f for f in self.model._meta.get_fields()
            if (getattr(f, 'many_to_one', False) and f.related_model != self.model)
        ]

        for related_field in related_fields:
            if path:
                cur_path = '%s__%s' % (path, related_field.name)
            else:
                cur_path = related_field.name

            if related_field.related_model == _obj._meta.model:
                path_list.append(Q(**{cur_path: _obj}))
            elif (related_field.related_model and
                    hasattr(related_field.related_model.objects, 'get_lookups')):
                path_list.extend(related_field.related_model.objects.get_lookups(
                    _obj, cur_path
                ))

        return path_list

    def _get_obj_related_lookups(self, _obj):
        lookups = []
        self.passed_models.append(self.model)
        for rel in self.model._meta.related_objects:
            null_filter = Q(**{'%s__isnull' % rel.field.name: False})

            if rel.related_model not in self.passed_models:
                is_rel_direct = isinstance(_obj, rel.related_model)
                qs = rel.related_model.objects

                if not is_rel_direct:
                    qs = qs.owned_by(_obj)

                related_queryset_result = qs.filter(null_filter).values_list(
                    rel.field.name, flat=True
                )

                if related_queryset_result:
                    q_name = 'id__in'
                    lookups.append(Q(**{q_name: related_queryset_result}))

                    if is_rel_direct:
                        break
        self.passed_models.remove(self.model)
        return lookups


class AbstractCompanyContactOwnerManager(AbstractObjectOwnerManager):
    def owned_by(self, company):
        try:
            return super().get_queryset().filter(
                Q(
                    relationships__company=company,
                    relationships__active=True
                ),
                Q(relationships__termination_date__isnull=True) |
                Q(relationships__termination_date__gte=date.today())
            )
        except ValueError:
            return super().owned_by(company)