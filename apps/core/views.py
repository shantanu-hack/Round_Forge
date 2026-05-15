from django.shortcuts import render

from apps.companies.models import Company


def home(request):
    companies = Company.objects.filter(is_active=True).order_by("order")
    return render(request, "core/home.html", {"companies": companies})
