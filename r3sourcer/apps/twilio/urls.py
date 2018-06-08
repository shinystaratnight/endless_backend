from django.conf.urls import url
from .views import SMSDialogTemplateView, IncomingSMSView

urlpatterns = [
    url(r'^$', SMSDialogTemplateView.as_view(), name='sms-view'),
    url(r'^incoming$', IncomingSMSView.as_view()),
]
