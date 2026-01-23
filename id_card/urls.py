from django.urls import path
from . import views

app_name = "id_card"

urlpatterns = [
    path("verify/<str:token>/", views.verify_id, name="verify"),
]
