from django.conf.urls import url

from r3sourcer.apps.billing import views


urlpatterns = [
    # billing page
    url(r'^billing/subscription/list/$', views.SubscriptionListView.as_view(), name='subscription_list'),
    url(r'^billing/subscription/create/$', views.SubscriptionCreateView.as_view(), name='subscription_create'),
    url(r'^billing/subscription/status/$', views.SubscriptionStatusView.as_view(), name='subscription_status'),
    url(r'^billing/subscription/cancel/$', views.SubscriptionCancelView.as_view(), name='subscription_cancel'),
    url(r'^billing/stripe_customer/$', views.StripeCustomerCreateView.as_view(), name='stripe_customer_create'),
    url(r'^billing/payments/$', views.PaymentListView.as_view(), name='payment_list'),
    url(r'^billing/check_payment_information/$', views.CheckPaymentInformationView.as_view(), name='check_payment_information'),
    url(r'^billing/disable_sms/(?P<id>[\w\-]+)$', views.DisableSMSFeatureView.as_view(), name='disable_sms'),

    # subscription management page
    url(r'^billing/companies/$', views.CompanyListView.as_view(), name='company_list'),
    url(r'^billing/discounts/$', views.DiscountView.as_view(), name='discounts'),
]
