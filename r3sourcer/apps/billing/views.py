from django.shortcuts import render


#  temporary view to help debug stripe integration
def billing_index(request):
    context = {}
    return render(request, 'billing/billing.html', context)
