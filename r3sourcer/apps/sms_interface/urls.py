from django.conf.urls import url
from .views import TemplateCompileView, ContentTypeListView, TemplateSMSMessageListView, SMSMessageListView, SearchObjects

urlpatterns = [
    url('^templates/$', TemplateSMSMessageListView.as_view(), name='templates'),
    url('^templates/compile/$', TemplateCompileView.as_view(), name='template-compile'),
    url('^find/contenttypes/$', ContentTypeListView.as_view(), name='find-contenttypes'),
    url(r'^find/objects/(?P<ct>\d+)/$', SearchObjects.as_view(), name='find-objects'),
    url('^message/$', SMSMessageListView.as_view(), name='sms_messages')
]