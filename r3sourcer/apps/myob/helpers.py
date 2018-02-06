from django.models import Q

from . api import MYOBClient
from . models import MYOBCompanyFileToken


def get_myob_client(cf_id=None, company=None, date=None, token_type=None):
    try:
        type_q = Q(type=token_type) if token_type else Q()

        if cf_id:
            cft = MYOBCompanyFileToken.objects.get(type_q, company_file__cf_id=cf_id)
        elif company:
            cft = company.company_file_tokens.enabled(date).filter(type_q).first()
        else:
            cft = MYOBCompanyFileToken.objects.filter(type_q).first()

        return MYOBClient(cf_data=cft)
    except Exception:
        return
