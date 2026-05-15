from django.urls import path

from apps.dashboard import views


app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("admin-insights/", views.admin_insights, name="admin_insights"),
]
