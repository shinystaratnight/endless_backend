from r3sourcer.apps.acceptance_tests.models import AcceptanceTestRelationship
from r3sourcer.apps.core.api.viewsets import BaseApiViewset
from r3sourcer.apps.core.utils.companies import get_site_master_company


class AcceptanceTestViewset(BaseApiViewset):

    def perform_create(self, serializer):
        instance = serializer.save()

        master_company = get_site_master_company(request=self.request)

        AcceptanceTestRelationship.objects.create(acceptance_test=instance, company=master_company)
