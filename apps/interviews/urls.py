from django.urls import path

from apps.interviews import views


app_name = "interviews"

urlpatterns = [
    path("<int:simulation_id>/", views.simulation_detail, name="simulation"),
    path("<int:simulation_id>/submit/", views.submit_answer_view, name="submit_answer"),
    path("<int:simulation_id>/expire/", views.expire_round_view, name="expire_round"),
    path("<int:simulation_id>/retry/", views.retry_view, name="retry"),
]
