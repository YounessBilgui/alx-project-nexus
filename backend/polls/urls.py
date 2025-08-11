

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PollViewSet, PollOptionViewSet, VoteViewSet, index, detail, results, vote
from .auth_views import register
from django.contrib.auth import views as auth_views

app_name = "polls"

router = DefaultRouter()
router.register(r"polls", PollViewSet, basename="polls")
router.register(r"options", PollOptionViewSet, basename="options")
router.register(r"votes", VoteViewSet, basename="votes")

urlpatterns = [
    path("api/", include(router.urls)),
    # Django template views
    path("polls/", index, name="index"),
    path("polls/<int:poll_id>/", detail, name="detail"),
    path("polls/<int:poll_id>/results/", results, name="results"),
    path("polls/<int:poll_id>/vote/", vote, name="vote"),
    # Named endpoints for DRF tests (these might conflict, so let's use different paths)
    path("api/polls/<int:pk>/", PollViewSet.as_view({"get": "retrieve"}), name="api_detail"),
    path("api/polls/", PollViewSet.as_view({"get": "list"}), name="api_index"),
    path("api/polls/<int:pk>/results/", PollViewSet.as_view({"get": "results"}), name="api_results"),
    path("api/polls/<int:pk>/vote/", PollViewSet.as_view({"post": "vote"}), name="api_vote"),
]
