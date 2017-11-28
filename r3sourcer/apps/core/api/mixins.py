class WorkflowStateSerializerFieldMixin():

    def get_method_fields(self):
        method_fields = list(super().get_method_fields())
        return method_fields + ['active_states']

    def get_active_states(self, obj):
        if not obj:
            return

        states = obj.get_active_states()

        return [
            state.state.name_after_activation or state.state.name_before_activation
            for state in states
        ]
