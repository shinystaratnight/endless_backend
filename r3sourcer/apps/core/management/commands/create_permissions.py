from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

from r3sourcer.apps.company_settings.models import GlobalPermission


METHODS = {
    "get": "Can view %s",
    "post": "Can create %s",
    "update": "Can change %s",
    "delete": "Can delete %s",
}

PERMISSION_LIST = [
    ("note", "core/notes"),
]

# put here verbose names of models to skip them
MODELS_TO_SKIP = [
    'Contact Notes',
]


class Command(BaseCommand):
    """
    Fetches list of models and creates CRUD permissions for them
    """
    def handle(self, *args, **kwargs):
        project_prefix = 'r3sourcer.apps.'
        app_list = list()

        for app in settings.INSTALLED_APPS:
            if project_prefix in app:
                app_list.append(app.split(project_prefix)[1])

        for app_name in app_list:
            models = apps.get_app_config(app_name).get_models()

            for model in models:
                if model._meta.verbose_name_plural in MODELS_TO_SKIP:
                    continue

                model_path = str("%s/%s" % (app_name.replace("_", "-"),
                                            model._meta.verbose_name_plural.replace(" ", "").lower()))

                for method, description in METHODS.items():
                    try:
                        GlobalPermission.objects.create(
                            name=description % model._meta.verbose_name.lower(),
                            codename='%s_%s' % (model_path, method)
                        )
                    except:
                        pass

        for verbose_name, model_path in PERMISSION_LIST:
            try:
                for method, description in METHODS.items():
                    GlobalPermission.objects.create(
                        name=verbose_name,
                        codename='%s_%s' % (model_path, method)
                    )
            except:
                pass

        self.stdout.write("Permissions created")
