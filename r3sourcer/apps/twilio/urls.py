from django.conf.urls import url
from .views import SMSDialogTemplateView

urlpatterns = [
    url(r'^$', SMSDialogTemplateView.as_view(), name='sms-view')
]