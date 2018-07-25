from django.conf.urls import url

from r3sourcer.apps.billing import views


urlpatterns = [
    # billing page
    url(r'^subscription/list/$', views.SubscriptionListView.as_view(), name='subscription_list'),
    url(r'^subscription/create/$', views.SubscriptionCreateView.as_view(), name='subscription_create'),
    url(r'^subscription/status/$', views.SubscriptionStatusView.as_view(), name='subscription_status'),
    url(r'^subscription/cancel/$', views.SubscriptionCancelView.as_view(), name='subscription_cancel'),
    url(r'^stripe_customer/$', views.StripeCustomerCreateView.as_view(), name='stripe_customer_create'),
    url(r'^payments/$', views.PaymentListView.as_view(), name='payment_list'),
    url(r'^check_payment_information/$', views.CheckPaymentInformationView.as_view(), name='check_payment_information'),

    # subscription management page
    url(r'^companies/$', views.CompanyListView.as_view(), name='company_list'),
    url(r'^discounts/$', views.DiscountView.as_view(), name='discounts'),
]
