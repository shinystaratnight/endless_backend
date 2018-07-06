from r3sourcer.apps.core.api.router import router

from . import models

router.register(models.AcceptanceTest)
router.register(models.AcceptanceTestQuestion)
router.register(models.AcceptanceTestAnswer)
router.register(models.AcceptanceTestSkill)
