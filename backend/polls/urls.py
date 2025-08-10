
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import PollViewSet
from .auth_views import register
from django.contrib.auth import views as auth_views

app_name = "polls"

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r"polls", PollViewSet, basename="polls")

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("api/", include(router.urls)),
    # API Authentication endpoints
    path("api/auth/register/", register, name="api_register"),
    # Django auth views for view tests
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", auth_views.LoginView.as_view(), name="register"),
]
