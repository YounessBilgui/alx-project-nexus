

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PollViewSet, PollOptionViewSet, VoteViewSet, index, detail, results, vote
from .auth_views import register
from django.contrib.auth import views as auth_views

app_name = "polls"

router = DefaultRouter()
router.register(r"polls", PollViewSet, basename="polls")
router.register(r"poll-options", PollOptionViewSet, basename="poll-options")
router.register(r"votes", VoteViewSet, basename="votes")

urlpatterns = [
    path("api/", include(router.urls)),
    # Nested poll options endpoint
    path("api/polls/<int:poll_id>/options/", PollOptionViewSet.as_view({"get": "list"}), name="poll-options-list"),
    # Django template views
    path("polls/", index, name="index"),
    path("polls/<int:poll_id>/", detail, name="detail"),
    path("polls/<int:poll_id>/results/", results, name="results"),
    path("polls/<int:poll_id>/vote/", vote, name="vote"),
]
