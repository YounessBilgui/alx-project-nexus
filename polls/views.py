from django.shortcuts import render
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Poll, PollOption, Vote
from .serializers import (
    PollSerializer, PollCreateSerializer, VoteSerializer, 
    PollResultSerializer
)


class PollViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing polls.
    
    Provides CRUD operations for polls including:
    - List all polls
    - Create new polls
    - Retrieve specific polls
    - Vote on polls
    - Get poll results
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
    
    @swagger_auto_schema(
        operation_description="List all active polls",
        responses={200: PollSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        """List all active polls."""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new poll with options",
        request_body=PollCreateSerializer,
        responses={
            201: PollSerializer,
            400: "Bad Request"
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new poll."""
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
        operation_description="Vote on a poll option",
        request_body=VoteSerializer,
        responses={
            200: openapi.Response("Vote recorded successfully"),
            400: "Bad Request - Invalid vote or duplicate voting"
        }
    )
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """
        Vote on a poll option.
        
        Validates that:
        - Poll is active and not expired
        - User hasn't already voted (based on IP)
        - Option exists for this poll
        """
        poll = self.get_object()
        voter_ip = self.get_client_ip(request)
        
        # Check if poll is active and not expired
        if not poll.is_active or poll.is_expired:
            return Response(
                {'error': 'Poll is not active or has expired'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already voted
        if Vote.objects.filter(poll=poll, voter_ip=voter_ip).exists():
            return Response(
                {'error': 'You have already voted in this poll'}, 
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
