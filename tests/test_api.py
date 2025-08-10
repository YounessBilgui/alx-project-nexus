"""
API Tests for the ALX Project Nexus - Online Poll System
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import json

# Import models from backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from polls.models import Poll, PollOption, Vote


class PollAPITest(APITestCase):
    """Test cases for Poll API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.poll_data = {
            'title': 'Test Poll',
            'description': 'Test Description',
            'expires_at': (timezone.now() + timedelta(hours=24)).isoformat()
        }
        
    def test_create_poll_authenticated(self):
        """Test creating poll with authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/polls/', self.poll_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Poll.objects.count(), 1)
        self.assertEqual(Poll.objects.get().title, 'Test Poll')
        
    def test_create_poll_unauthenticated(self):
        """Test creating poll without authentication"""
        response = self.client.post('/api/polls/', self.poll_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_list_polls(self):
        """Test listing polls"""
        # Create test polls
        poll1 = Poll.objects.create(
            title="Poll 1",
            description="Description 1",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        poll2 = Poll.objects.create(
            title="Poll 2",
            description="Description 2",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=48)
        )
        
        response = self.client.get('/api/polls/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
    def test_poll_detail(self):
        """Test retrieving poll detail"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        response = self.client.get(f'/api/polls/{poll.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Poll')
        
    def test_update_poll_owner(self):
        """Test updating poll by owner"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        self.client.force_authenticate(user=self.user)
        updated_data = {
            'title': 'Updated Poll',
            'description': 'Updated Description',
            'expires_at': (timezone.now() + timedelta(hours=48)).isoformat()
        }
        
        response = self.client.put(f'/api/polls/{poll.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        poll.refresh_from_db()
        self.assertEqual(poll.title, 'Updated Poll')
        
    def test_delete_poll_owner(self):
        """Test deleting poll by owner"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/polls/{poll.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Poll.objects.count(), 0)
        
    def test_update_poll_non_owner(self):
        """Test updating poll by non-owner"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=other_user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        self.client.force_authenticate(user=self.user)
        updated_data = {'title': 'Hacked Poll'}
        
        response = self.client.put(f'/api/polls/{poll.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PollOptionAPITest(APITestCase):
    """Test cases for PollOption API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
    def test_create_poll_option(self):
        """Test creating poll option"""
        self.client.force_authenticate(user=self.user)
        option_data = {
            'poll': self.poll.id,
            'text': 'Option 1'
        }
        
        response = self.client.post('/api/poll-options/', option_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PollOption.objects.count(), 1)
        
    def test_list_poll_options(self):
        """Test listing poll options for a poll"""
        option1 = PollOption.objects.create(poll=self.poll, text="Option 1")
        option2 = PollOption.objects.create(poll=self.poll, text="Option 2")
        
        response = self.client.get(f'/api/polls/{self.poll.id}/options/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
    def test_update_poll_option_owner(self):
        """Test updating poll option by poll owner"""
        option = PollOption.objects.create(poll=self.poll, text="Option 1")
        
        self.client.force_authenticate(user=self.user)
        updated_data = {'text': 'Updated Option'}
        
        response = self.client.put(f'/api/poll-options/{option.id}/', updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        option.refresh_from_db()
        self.assertEqual(option.text, 'Updated Option')
        
    def test_delete_poll_option_owner(self):
        """Test deleting poll option by poll owner"""
        option = PollOption.objects.create(poll=self.poll, text="Option 1")
        
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/poll-options/{option.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PollOption.objects.count(), 0)


class VoteAPITest(APITestCase):
    """Test cases for Vote API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        self.option1 = PollOption.objects.create(poll=self.poll, text="Option 1")
        self.option2 = PollOption.objects.create(poll=self.poll, text="Option 2")
        
    def test_cast_vote(self):
        """Test casting a vote"""
        vote_data = {
            'poll': self.poll.id,
            'option': self.option1.id
        }
        
        response = self.client.post('/api/votes/', vote_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Vote.objects.count(), 1)
        
    def test_duplicate_vote_prevention(self):
        """Test that duplicate votes from same IP are prevented"""
        vote_data = {
            'poll': self.poll.id,
            'option': self.option1.id
        }
        
        # First vote
        response1 = self.client.post('/api/votes/', vote_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second vote from same IP
        response2 = self.client.post('/api/votes/', vote_data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Vote.objects.count(), 1)
        
    def test_vote_on_expired_poll(self):
        """Test voting on expired poll"""
        expired_poll = Poll.objects.create(
            title="Expired Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        expired_option = PollOption.objects.create(poll=expired_poll, text="Option 1")
        
        vote_data = {
            'poll': expired_poll.id,
            'option': expired_option.id
        }
        
        response = self.client.post('/api/votes/', vote_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_get_poll_results(self):
        """Test getting poll results"""
        # Create some votes
        Vote.objects.create(poll=self.poll, option=self.option1, voter_ip="192.168.1.1")
        Vote.objects.create(poll=self.poll, option=self.option1, voter_ip="192.168.1.2")
        Vote.objects.create(poll=self.poll, option=self.option2, voter_ip="192.168.1.3")
        
        response = self.client.get(f'/api/polls/{self.poll.id}/results/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should contain vote counts
        self.assertIn('results', response.data)
        

class AuthenticationAPITest(APITestCase):
    """Test API authentication"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
    def test_user_registration(self):
        """Test user registration via API"""
        response = self.client.post('/api/auth/register/', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())
        
    def test_user_login(self):
        """Test user login via API"""
        user = User.objects.create_user(**self.user_data)
        
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/auth/login/', login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        
    def test_jwt_token_authentication(self):
        """Test JWT token authentication"""
        user = User.objects.create_user(**self.user_data)
        
        # Get token
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/auth/login/', login_data, format='json')
        token = response.data['token']
        
        # Use token for authenticated request
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        poll_data = {
            'title': 'Test Poll',
            'description': 'Test Description',
            'expires_at': (timezone.now() + timedelta(hours=24)).isoformat()
        }
        
        response = self.client.post('/api/polls/', poll_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class RateLimitingAPITest(APITestCase):
    """Test API rate limiting"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
    def test_rate_limiting_on_vote_endpoint(self):
        """Test rate limiting on vote endpoint"""
        # This would test the actual rate limiting implementation
        # Multiple rapid requests should be limited
        pass
        
    def test_rate_limiting_on_poll_creation(self):
        """Test rate limiting on poll creation"""
        # Test that users can't create too many polls too quickly
        pass


class DataValidationAPITest(APITestCase):
    """Test API data validation"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
    def test_poll_validation_empty_title(self):
        """Test poll validation with empty title"""
        poll_data = {
            'title': '',
            'description': 'Test Description',
            'expires_at': (timezone.now() + timedelta(hours=24)).isoformat()
        }
        
        response = self.client.post('/api/polls/', poll_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_poll_validation_past_expiry(self):
        """Test poll validation with past expiry date"""
        poll_data = {
            'title': 'Test Poll',
            'description': 'Test Description',
            'expires_at': (timezone.now() - timedelta(hours=1)).isoformat()
        }
        
        response = self.client.post('/api/polls/', poll_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_option_validation_empty_text(self):
        """Test option validation with empty text"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        option_data = {
            'poll': poll.id,
            'text': ''
        }
        
        response = self.client.post('/api/poll-options/', option_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
