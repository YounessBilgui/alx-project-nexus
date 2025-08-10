from django.shortcuts import render
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Poll, PollOption, Vote
from .serializers import (
    PollSerializer, PollCreateSerializer, VoteSerializer, 
    PollResultSerializer
)


# Custom throttle classes for specific operations
class VotingRateThrottle(UserRateThrottle):
    scope = 'voting'

class PollCreationRateThrottle(UserRateThrottle):
    scope = 'poll_creation'


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
        if self.action == 'create':
            return PollCreateSerializer
        elif self.action == 'results':
            return PollResultSerializer
        return PollSerializer
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_throttles(self):
        """Set throttles based on action."""
        if self.action == 'create':
            throttle_classes = [PollCreationRateThrottle]
        elif self.action == 'vote':
            throttle_classes = [VotingRateThrottle]
        else:
            throttle_classes = [AnonRateThrottle, UserRateThrottle]
        return [throttle() for throttle in throttle_classes]
    
    @swagger_auto_schema(
        operation_description="List all active polls",
        responses={200: PollSerializer(many=True)}
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
            429: "Too Many Requests - Rate limit exceeded (5 polls per hour)"
        }
    )
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True))
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
        responses={200: PollSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific poll."""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        method='post',
        operation_description="Vote on a poll option (Rate limited: 10 votes per minute)",
        request_body=VoteSerializer,
        responses={
            200: openapi.Response("Vote recorded successfully"),
            400: "Bad Request - Invalid vote or duplicate voting",
            429: "Too Many Requests - Rate limit exceeded"
        }
    )
    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    @action(detail=True, methods=['post'])
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
                {
                    'error': 'Poll is not active or has expired',
                    'code': 'POLL_INACTIVE'
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already voted
        if Vote.objects.filter(poll=poll, voter_ip=voter_ip).exists():
            return Response(
                {
                    'error': 'You have already voted in this poll',
                    'code': 'DUPLICATE_VOTE'
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate vote data
        serializer = VoteSerializer(
            data=request.data, 
            context={'poll_id': poll.id}
        )
        serializer.is_valid(raise_exception=True)
        
        option_id = serializer.validated_data['option_id']
        
        try:
            option = poll.options.get(id=option_id)
            
            # Create vote record and increment count atomically
            with transaction.atomic():
                Vote.objects.create(
                    poll=poll, 
                    option=option, 
                    voter_ip=voter_ip
                )
                PollOption.objects.filter(id=option_id).update(
                    vote_count=F('vote_count') + 1
                )
            
            return Response({
                'message': 'Vote recorded successfully',
                'option': option.text,
                'poll': poll.title
            })
            
        except PollOption.DoesNotExist:
            return Response(
                {'error': 'Invalid option'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @swagger_auto_schema(
        operation_description="Get poll results with vote counts and percentages",
        responses={200: PollResultSerializer}
    )
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get poll results with vote counts and percentages."""
        poll = self.get_object()
        serializer = PollResultSerializer(poll)
        return Response(serializer.data)
    
    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
