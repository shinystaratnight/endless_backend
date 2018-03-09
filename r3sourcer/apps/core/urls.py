from django.conf.urls import url

from r3sourcer.apps.core import views


urlpatterns = [
    url(r'^invoices/(?P<id>[\w\-]+)/approve/$', views.ApproveInvoiceView.as_view(), name='approve_invoice'),
]
