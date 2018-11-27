from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class ContactBackend(ModelBackend):

    def get_login_value(self, model, **kwargs):
        value = None
        for field in model.REQUIRED_FIELDS:
            value = kwargs.get(field)
            if value is not None:
                return value
        return value

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = self.get_login_value(UserModel, **kwargs)

        if not username or not password:
            return

        params = Q()
        for field in UserModel.REQUIRED_FIELDS:
            field_name = 'contact__{}'.format(field)
            params |= Q(**{field_name: username})

        try:
            user = UserModel._default_manager.get(params)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password):
                return user
