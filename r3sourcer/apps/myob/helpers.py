from . api import MYOBClient
from . models import MYOBCompanyFileToken


def get_myob_client(cf_id=None, company=None):
    try:
        if company:
            cft = company.myobcompanyfiletoken
        elif cf_id:
            cft = MYOBCompanyFileToken.objects.get(company_file__cf_id=cf_id)
        else:
            cft = MYOBCompanyFileToken.objects.first()

        return MYOBClient(cf_data=cft)
    except Exception:
        return
