from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .models import Poll, PollOption, Vote
from .serializers import (
    PollCreateSerializer,
    PollOptionStandaloneSerializer,
    PollOptionUpdateSerializer,
    PollResultSerializer,
    PollSerializer,
    PollUpdateSerializer,
    VoteCreateSerializer,
    VoteSerializer,
)


# Custom throttle classes for specific operations
class VotingRateThrottle(UserRateThrottle):
    scope = "voting"


class PollCreationRateThrottle(UserRateThrottle):
    scope = "poll_creation"


class PollViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing polls with JWT authentication and rate limiting.

    Provides CRUD operations for polls including:
    - List all polls (public, rate limited)
    - Create new polls (authenticated users only, rate limited)
    - Retrieve specific polls (public)
    - Vote on polls (rate limited)
    - Get poll results (public)
    """

    queryset = Poll.objects.filter(is_active=True)

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return PollCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return PollUpdateSerializer
        elif self.action == "results":
            return PollResultSerializer
        return PollSerializer

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def check_object_permissions(self, request, obj):
        """Check if user has permission to modify this poll."""
        super().check_object_permissions(request, obj)

        # For update/delete actions, only poll owner can modify
        if self.action in ["update", "partial_update", "destroy"]:
            if obj.created_by != request.user:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("You can only modify polls you created.")

    def get_throttles(self):
        """Set throttles based on action."""
        if self.action == "create":
            throttle_classes = [PollCreationRateThrottle]
        elif self.action == "vote":
            throttle_classes = [VotingRateThrottle]
        else:
            throttle_classes = [AnonRateThrottle, UserRateThrottle]
        return [throttle() for throttle in throttle_classes]

    @swagger_auto_schema(
        operation_description="List all active polls",
        responses={200: PollSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """List all active polls."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new poll with options (Rate limited: 5 polls per hour)",
        request_body=PollCreateSerializer,
        responses={
            201: PollSerializer,
            400: "Bad Request",
            429: "Too Many Requests - Rate limit exceeded (5 polls per hour)",
        },
    )
    @method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True))
    def create(self, request, *args, **kwargs):
        """
        Create a new poll with rate limiting.

        Rate Limited: 5 polls per hour per IP address.
        Requires authentication.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = serializer.save()

        # Return the created poll with full details
        response_serializer = PollSerializer(poll)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Get details of a specific poll",
        responses={200: PollSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific poll."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        method="post",
        operation_description="Vote on a poll option (Rate limited: 10 votes per minute)",
        request_body=VoteSerializer,
        responses={
            200: openapi.Response("Vote recorded successfully"),
            400: "Bad Request - Invalid vote or duplicate voting",
            429: "Too Many Requests - Rate limit exceeded",
        },
    )
    @method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True))
    @action(detail=True, methods=["post"])
    def vote(self, request, pk=None):
        """
        Vote on a poll option with rate limiting.

        Rate Limited: 10 votes per minute per IP address.

        Validates that:
        - Poll is active and not expired
        - User hasn't already voted (based on IP)
        - Option exists for this poll
        - Rate limit not exceeded
        """
        poll = self.get_object()
        voter_ip = self.get_client_ip(request)

        # Check if poll is active and not expired
        if not poll.is_active or poll.is_expired:
            return Response(
                {"error": "Poll is not active or has expired", "code": "POLL_INACTIVE"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if user already voted
        if Vote.objects.filter(poll=poll, voter_ip=voter_ip).exists():
            return Response(
                {
                    "error": "You have already voted in this poll",
                    "code": "DUPLICATE_VOTE",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate vote data
        serializer = VoteSerializer(data=request.data, context={"poll_id": poll.id})
        serializer.is_valid(raise_exception=True)

        option_id = serializer.validated_data["option_id"]

        try:
            option = poll.options.get(id=option_id)

            # Create vote record and increment count atomically
            with transaction.atomic():
                Vote.objects.create(poll=poll, option=option, voter_ip=voter_ip)
                PollOption.objects.filter(id=option_id).update(
                    vote_count=F("vote_count") + 1
                )

            return Response(
                {
                    "message": "Vote recorded successfully",
                    "option": option.text,
                    "poll": poll.title,
                }
            )

        except PollOption.DoesNotExist:
            return Response(
                {"error": "Invalid option"}, status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        operation_description="Get poll results with vote counts and percentages",
        responses={200: PollResultSerializer},
    )
    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        """Get poll results with vote counts and percentages."""
        poll = self.get_object()
        serializer = PollResultSerializer(poll)
        return Response(serializer.data)

    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class PollOptionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing poll options."""

    queryset = PollOption.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ["update", "partial_update"]:
            return PollOptionUpdateSerializer
        return PollOptionStandaloneSerializer

    def get_queryset(self):
        """Filter options by poll if poll_pk or poll_id is provided."""
        queryset = PollOption.objects.all()
        # Check for both poll_pk (router) and poll_id (custom URL)
        poll_pk = self.kwargs.get("poll_pk") or self.kwargs.get("poll_id")
        if poll_pk:
            queryset = queryset.filter(poll_id=poll_pk)
        return queryset


class VoteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing votes."""

    queryset = Vote.objects.all()
    serializer_class = VoteCreateSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Filter votes by poll if needed."""
        return Vote.objects.all()

    def create(self, request, *args, **kwargs):
        """Create a vote with duplicate prevention."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get IP address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            voter_ip = x_forwarded_for.split(",")[0]
        else:
            voter_ip = request.META.get("REMOTE_ADDR", "127.0.0.1")

        poll = serializer.validated_data["poll"]
        option = serializer.validated_data["option"]

        # Check for duplicate vote
        if Vote.objects.filter(poll=poll, voter_ip=voter_ip).exists():
            return Response(
                {"error": "You have already voted in this poll"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the vote
        vote = serializer.save(voter_ip=voter_ip)

        # Update option vote count
        from django.db.models import F

        option.vote_count = F("vote_count") + 1
        option.save(update_fields=["vote_count"])

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VoteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing votes."""

    queryset = Vote.objects.all()
    serializer_class = VoteCreateSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Filter votes by poll if needed."""
        return Vote.objects.all()

    def create(self, request, *args, **kwargs):
        """Create a vote with duplicate prevention."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get IP address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            voter_ip = x_forwarded_for.split(",")[0]
        else:
            voter_ip = request.META.get("REMOTE_ADDR", "127.0.0.1")

        poll = serializer.validated_data["poll"]
        option = serializer.validated_data["option"]

        # Check if poll is expired
        if poll.is_expired:
            return Response(
                {"error": "Poll has expired"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check for duplicate vote
        if Vote.objects.filter(poll=poll, voter_ip=voter_ip).exists():
            return Response(
                {"error": "You have already voted in this poll"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the vote
        vote = serializer.save(voter_ip=voter_ip)

        # Update option vote count atomically
        PollOption.objects.filter(id=option.id).update(vote_count=F("vote_count") + 1)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# Django template views for tests
def index(request):
    """Poll list view."""
    latest_poll_list = Poll.objects.filter(is_active=True).order_by("-created_at")[:5]
    context = {"latest_poll_list": latest_poll_list}
    return render(request, "polls/index.html", context)


def detail(request, poll_id):
    """Poll detail view."""
    poll = get_object_or_404(Poll, pk=poll_id)
    return render(request, "polls/detail.html", {"poll": poll})


def results(request, poll_id):
    """Poll results view."""
    poll = get_object_or_404(Poll, pk=poll_id)
    return render(request, "polls/results.html", {"poll": poll})


def vote(request, poll_id):
    """Vote on a poll."""
    poll = get_object_or_404(Poll, pk=poll_id)

    if request.method == "POST":
        try:
            selected_option = poll.options.get(pk=request.POST["choice"])
        except (KeyError, PollOption.DoesNotExist):
            return render(
                request,
                "polls/detail.html",
                {
                    "poll": poll,
                    "error_message": "You didn't select a choice.",
                },
            )
        except ValueError:
            # Handle case where choice is not a valid integer
            return render(
                request,
                "polls/detail.html",
                {
                    "poll": poll,
                    "error_message": "You didn't select a choice.",
                },
            )

        # Create vote
        voter_ip = request.META.get("REMOTE_ADDR")

        # Check for duplicate votes
        if Vote.objects.filter(poll=poll, voter_ip=voter_ip).exists():
            return render(
                request,
                "polls/detail.html",
                {
                    "poll": poll,
                    "error_message": "You have already voted in this poll.",
                },
            )

        Vote.objects.create(poll=poll, option=selected_option, voter_ip=voter_ip)

        # Update option vote count
        selected_option.vote_count += 1
        selected_option.save()

        return redirect("polls:results", poll_id=poll.id)

    return render(request, "polls/detail.html", {"poll": poll})
