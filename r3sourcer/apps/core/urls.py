from django.conf.urls import url

from r3sourcer.apps.core import views


urlpatterns = [
    url(r'^core/invoices/(?P<id>[\w\-]+)/approve/$', views.ApproveInvoiceView.as_view(), name='approve_invoice'),
    url(r'^core/invoices/sync/$', views.SyncInvoicesView.as_view(), name='sync_invoices'),
]
