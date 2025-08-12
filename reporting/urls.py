from django.urls import path
from . import views

app_name = "reporting"

urlpatterns = [
    path("", views.run_list, name="run_list"),
    path("run/<int:result_id>/", views.run_detail, name="run_detail"),
]
