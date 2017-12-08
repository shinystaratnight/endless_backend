from drf_auto_endpoint.router import router

from r3sourcer.apps.sms_interface import models as sms_models

router.register(sms_models.SMSMessage)
router.register(sms_models.SMSRelatedObject)
