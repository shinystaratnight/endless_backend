from django_filters.filters import ChoiceFilter


class ValuesFilter(ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager
        qs = qs.order_by(self.name).values_list(
            self.name, flat=True
        ).distinct()
        self.extra['choices'] = [(o, o) for o in qs]
        return super(ValuesFilter, self).field
