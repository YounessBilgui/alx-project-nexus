"""
Test views for the ALX Project Nexus - Online Poll System
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

# Import models from backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from polls.models import Poll, PollOption, Vote


class PollListViewTest(TestCase):
    """Test cases for poll list view"""
    
    def setUp(self):
        """Set up test data and client"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test polls
        self.active_poll = Poll.objects.create(
            title="Active Poll",
            description="An active poll",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        self.expired_poll = Poll.objects.create(
            title="Expired Poll",
            description="An expired poll",
            created_by=self.user,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
    def test_poll_list_view_accessible(self):
        """Test that poll list view is accessible"""
        response = self.client.get(reverse('polls:index'))
        self.assertEqual(response.status_code, 200)
        
    def test_poll_list_shows_active_polls(self):
        """Test that active polls are shown in list"""
        response = self.client.get(reverse('polls:index'))
        self.assertContains(response, "Active Poll")
        
    def test_poll_list_context_data(self):
        """Test poll list view context data"""
        response = self.client.get(reverse('polls:index'))
        self.assertIn('latest_poll_list', response.context)
        polls = response.context['latest_poll_list']
        self.assertIn(self.active_poll, polls)


class PollDetailViewTest(TestCase):
    """Test cases for poll detail view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
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
        
        self.option1 = PollOption.objects.create(
            poll=self.poll,
            text="Option 1"
        )
        self.option2 = PollOption.objects.create(
            poll=self.poll,
            text="Option 2"
        )
        
    def test_poll_detail_view_accessible(self):
        """Test that poll detail view is accessible"""
        response = self.client.get(reverse('polls:detail', args=[self.poll.id]))
        self.assertEqual(response.status_code, 200)
        
    def test_poll_detail_shows_poll_info(self):
        """Test that poll detail shows poll information"""
        response = self.client.get(reverse('polls:detail', args=[self.poll.id]))
        self.assertContains(response, self.poll.title)
        self.assertContains(response, self.poll.description)
        
    def test_poll_detail_shows_options(self):
        """Test that poll detail shows poll options"""
        response = self.client.get(reverse('polls:detail', args=[self.poll.id]))
        self.assertContains(response, "Option 1")
        self.assertContains(response, "Option 2")
        
    def test_poll_detail_nonexistent_poll(self):
        """Test accessing detail of non-existent poll"""
        response = self.client.get(reverse('polls:detail', args=[999]))
        self.assertEqual(response.status_code, 404)


class VoteViewTest(TestCase):
    """Test cases for voting functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
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
        
        self.option1 = PollOption.objects.create(
            poll=self.poll,
            text="Option 1"
        )
        self.option2 = PollOption.objects.create(
            poll=self.poll,
            text="Option 2"
        )
        
    def test_successful_vote(self):
        """Test successful voting"""
        response = self.client.post(
            reverse('polls:vote', args=[self.poll.id]),
            {'choice': self.option1.id}
        )
        
        # Should redirect to results page
        self.assertEqual(response.status_code, 302)
        
        # Verify vote was created
        self.assertTrue(
            Vote.objects.filter(
                poll=self.poll,
                option=self.option1
            ).exists()
        )
        
    def test_vote_without_selection(self):
        """Test voting without selecting an option"""
        response = self.client.post(
            reverse('polls:vote', args=[self.poll.id]),
            {}
        )
        
        # Should show error message (check for HTML-escaped version)
        self.assertContains(response, "You didn&#x27;t select a choice")
        
        # Verify no vote was created
        self.assertEqual(Vote.objects.filter(poll=self.poll).count(), 0)
        
    def test_vote_invalid_option(self):
        """Test voting with invalid option"""
        response = self.client.post(
            reverse('polls:vote', args=[self.poll.id]),
            {'choice': 999}
        )
        
        # Should show error message (check for HTML-escaped version)
        self.assertContains(response, "You didn&#x27;t select a choice")
        
    def test_duplicate_vote_prevention(self):
        """Test that duplicate votes are prevented"""
        # First vote
        self.client.post(
            reverse('polls:vote', args=[self.poll.id]),
            {'choice': self.option1.id}
        )
        
        # Second vote from same IP
        response = self.client.post(
            reverse('polls:vote', args=[self.poll.id]),
            {'choice': self.option2.id}
        )
        
        # Should show error or handle appropriately
        # Only one vote should exist
        self.assertEqual(Vote.objects.filter(poll=self.poll).count(), 1)


class ResultsViewTest(TestCase):
    """Test cases for poll results view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
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
        
        self.option1 = PollOption.objects.create(
            poll=self.poll,
            text="Option 1"
        )
        self.option2 = PollOption.objects.create(
            poll=self.poll,
            text="Option 2"
        )
        
        # Create some votes
        Vote.objects.create(
            poll=self.poll,
            option=self.option1,
            voter_ip="192.168.1.1"
        )
        Vote.objects.create(
            poll=self.poll,
            option=self.option1,
            voter_ip="192.168.1.2"
        )
        Vote.objects.create(
            poll=self.poll,
            option=self.option2,
            voter_ip="192.168.1.3"
        )
        
    def test_results_view_accessible(self):
        """Test that results view is accessible"""
        response = self.client.get(reverse('polls:results', args=[self.poll.id]))
        self.assertEqual(response.status_code, 200)
        
    def test_results_shows_vote_counts(self):
        """Test that results show vote counts"""
        response = self.client.get(reverse('polls:results', args=[self.poll.id]))
        self.assertContains(response, "Option 1")
        self.assertContains(response, "Option 2")
        # Should show vote counts (2 for option1, 1 for option2)
        
    def test_results_nonexistent_poll(self):
        """Test accessing results of non-existent poll"""
        response = self.client.get(reverse('polls:results', args=[999]))
        self.assertEqual(response.status_code, 404)


class AuthenticationTest(TestCase):
    """Test authentication-related functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_user_login(self):
        """Test user login functionality"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)
        
    def test_user_logout(self):
        """Test user logout functionality"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('logout'))
        
        # Should redirect after logout
        self.assertEqual(response.status_code, 302)
        
    def test_login_required_views(self):
        """Test that login is required for protected views"""
        # This test would depend on which views require authentication
        pass


class SecurityTest(TestCase):
    """Test security features"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
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
        
    def test_csrf_protection(self):
        """Test CSRF protection on forms"""
        # Create a client that enforces CSRF protection
        from django.test.client import Client
        csrf_client = Client(enforce_csrf_checks=True)
        
        response = csrf_client.post(
            reverse('polls:vote', args=[self.poll.id]),
            {'choice': 1}
        )
        # Should fail due to missing CSRF token
        self.assertEqual(response.status_code, 403)
        
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # This would test the rate limiting middleware
        # Multiple rapid requests should be limited
        pass
        
    def test_sql_injection_protection(self):
        """Test protection against SQL injection"""
        # Django ORM provides protection, but we can test with malicious input
        malicious_input = "'; DROP TABLE polls_poll; --"
        response = self.client.get(f"/polls/search/?q={malicious_input}")
        # Should not cause any issues
        
    def test_xss_protection(self):
        """Test protection against XSS attacks"""
        # Test that user input is properly escaped
        pass
