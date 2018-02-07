from . api import MYOBClient
from . models import MYOBCompanyFileToken


def get_myob_client(cf_id=None, company=None, date=None):
    try:
        if cf_id:
            cft = MYOBCompanyFileToken.objects.get(company_file__cf_id=cf_id)
        elif company:
            cft = company.company_file_tokens.enabled(date).first()
        else:
            cft = MYOBCompanyFileToken.objects.all().first()

        return MYOBClient(cf_data=cft)
    except Exception:
        return
