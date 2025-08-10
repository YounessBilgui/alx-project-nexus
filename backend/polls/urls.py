

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import PollViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from django.contrib.auth import views as auth_views

app_name = "polls"

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r"polls", PollViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("api/", include(router.urls)),
    # Authentication endpoints
    path("api/auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("api/auth/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/auth/register/", auth_views.LoginView.as_view(), name="register"),  # Replace with custom register view if exists
    # Named poll endpoints for reverse lookups
    path("api/polls/<int:pk>/", PollViewSet.as_view({"get": "retrieve"}), name="detail"),
    path("api/polls/", PollViewSet.as_view({"get": "list"}), name="index"),
    path("api/polls/<int:pk>/results/", PollViewSet.as_view({"get": "results"}), name="results"),
    path("api/polls/<int:pk>/vote/", PollViewSet.as_view({"post": "vote"}), name="vote"),
]
