from django_filters.filters import ChoiceFilter, DateFromToRangeFilter, DateTimeFromToRangeFilter


class DistinctFilterMixin:

    def filter(self, qs, value):
        qs = super().filter(qs, value)
        if self.distinct:
            qs = qs.distinct()

        return qs


class ValuesFilter(ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager
        qs = qs.order_by(self.name).values_list(
            self.name, flat=True
        ).distinct()
        self.extra['choices'] = [(o, o) for o in qs]
        return super(ValuesFilter, self).field


class DateRangeFilter(DistinctFilterMixin, DateFromToRangeFilter):
    pass


class DateTimeRangeFilter(DistinctFilterMixin, DateTimeFromToRangeFilter):
    pass
