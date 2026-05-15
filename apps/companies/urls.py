from django.urls import path

from apps.companies import views


app_name = "companies"

urlpatterns = [
    path("", views.company_list, name="list"),
    path("<slug:slug>/", views.company_detail, name="detail"),
    path("<slug:slug>/start/", views.start_company_simulation, name="start"),
]
