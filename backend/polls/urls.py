

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PollViewSet
from .auth_views import register
from django.contrib.auth import views as auth_views

app_name = "polls"

router = DefaultRouter()
router.register(r"polls", PollViewSet, basename="polls")

urlpatterns = [
    path("api/", include(router.urls)),
    # Auth endpoints for Django views
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),
    # Named endpoints for DRF tests
    path("polls/<int:pk>/", PollViewSet.as_view({"get": "retrieve"}), name="detail"),
    path("polls/", PollViewSet.as_view({"get": "list"}), name="index"),
    path("polls/<int:pk>/results/", PollViewSet.as_view({"get": "results"}), name="results"),
    path("polls/<int:pk>/vote/", PollViewSet.as_view({"post": "vote"}), name="vote"),
]
