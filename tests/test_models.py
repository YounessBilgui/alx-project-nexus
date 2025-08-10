"""
Test models for the ALX Project Nexus - Online Poll System
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError

# Import models from backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from polls.models import Poll, PollOption, Vote


class PollModelTest(TestCase):
    """Test cases for Poll model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            password='testpass123'
        )
        
    def test_poll_creation(self):
        """Test poll creation with valid data"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        self.assertEqual(poll.title, "Test Poll")
        self.assertEqual(poll.description, "Test Description")
        self.assertEqual(poll.created_by, self.user)
        self.assertTrue(poll.is_active)
        self.assertFalse(poll.is_expired)
        
    def test_poll_expiry(self):
        """Test poll expiry functionality"""
        expired_poll = Poll.objects.create(
            title="Expired Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        self.assertTrue(expired_poll.is_expired)
        
    def test_poll_str_representation(self):
        """Test poll string representation"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        self.assertEqual(str(poll), "Test Poll")
        
    def test_poll_total_votes_property(self):
        """Test poll total votes calculation"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Initially should have 0 votes
        self.assertEqual(poll.total_votes, 0)


class PollOptionModelTest(TestCase):
    """Test cases for PollOption model"""
    
    def setUp(self):
        """Set up test data"""
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
        
    def test_poll_option_creation(self):
        """Test poll option creation"""
        option = PollOption.objects.create(
            poll=self.poll,
            text="Option 1"
        )
        self.assertEqual(option.text, "Option 1")
        self.assertEqual(option.poll, self.poll)
        self.assertEqual(option.vote_count, 0)
        
    def test_poll_option_str_representation(self):
        """Test poll option string representation"""
        option = PollOption.objects.create(
            poll=self.poll,
            text="Option 1"
        )
        self.assertEqual(str(option), "Option 1")
        
    def test_multiple_options_for_poll(self):
        """Test creating multiple options for a poll"""
        option1 = PollOption.objects.create(poll=self.poll, text="Option 1")
        option2 = PollOption.objects.create(poll=self.poll, text="Option 2")
        option3 = PollOption.objects.create(poll=self.poll, text="Option 3")
        
        self.assertEqual(self.poll.options.count(), 3)
        self.assertIn(option1, self.poll.options.all())
        self.assertIn(option2, self.poll.options.all())
        self.assertIn(option3, self.poll.options.all())


class VoteModelTest(TestCase):
    """Test cases for Vote model"""
    
    def setUp(self):
        """Set up test data"""
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
        self.option = PollOption.objects.create(
            poll=self.poll,
            text="Option 1"
        )
        
    def test_vote_creation(self):
        """Test vote creation"""
        vote = Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_ip="192.168.1.1"
        )
        self.assertEqual(vote.poll, self.poll)
        self.assertEqual(vote.option, self.option)
        self.assertEqual(vote.voter_ip, "192.168.1.1")
        self.assertIsNotNone(vote.voted_at)
        
    def test_vote_str_representation(self):
        """Test vote string representation"""
        vote = Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_ip="192.168.1.1"
        )
        expected_str = f"Vote for {self.option.text} in {self.poll.title}"
        self.assertEqual(str(vote), expected_str)
        
    def test_duplicate_vote_prevention(self):
        """Test that duplicate votes from same IP are prevented"""
        # Create first vote
        Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_ip="192.168.1.1"
        )
        
        # Try to create duplicate vote from same IP
        with self.assertRaises(IntegrityError):
            Vote.objects.create(
                poll=self.poll,
                option=self.option,
                voter_ip="192.168.1.1"
            )
            
    def test_multiple_votes_different_ips(self):
        """Test that multiple votes from different IPs are allowed"""
        vote1 = Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_ip="192.168.1.1"
        )
        
        vote2 = Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_ip="192.168.1.2"
        )
        
        self.assertEqual(Vote.objects.filter(poll=self.poll).count(), 2)
        self.assertNotEqual(vote1.voter_ip, vote2.voter_ip)


class ModelRelationshipTest(TestCase):
    """Test model relationships and cascading deletes"""
    
    def setUp(self):
        """Set up test data"""
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
        
    def test_poll_deletion_cascades_to_options(self):
        """Test that deleting a poll deletes its options"""
        poll_id = self.poll.id
        option1_id = self.option1.id
        option2_id = self.option2.id
        
        # Verify options exist
        self.assertTrue(PollOption.objects.filter(id=option1_id).exists())
        self.assertTrue(PollOption.objects.filter(id=option2_id).exists())
        
        # Delete poll
        self.poll.delete()
        
        # Verify options are deleted
        self.assertFalse(PollOption.objects.filter(id=option1_id).exists())
        self.assertFalse(PollOption.objects.filter(id=option2_id).exists())
        
    def test_poll_deletion_cascades_to_votes(self):
        """Test that deleting a poll deletes its votes"""
        vote1 = Vote.objects.create(
            poll=self.poll,
            option=self.option1,
            voter_ip="192.168.1.1"
        )
        vote2 = Vote.objects.create(
            poll=self.poll,
            option=self.option2,
            voter_ip="192.168.1.2"
        )
        
        vote1_id = vote1.id
        vote2_id = vote2.id
        
        # Verify votes exist
        self.assertTrue(Vote.objects.filter(id=vote1_id).exists())
        self.assertTrue(Vote.objects.filter(id=vote2_id).exists())
        
        # Delete poll
        self.poll.delete()
        
        # Verify votes are deleted
        self.assertFalse(Vote.objects.filter(id=vote1_id).exists())
        self.assertFalse(Vote.objects.filter(id=vote2_id).exists())
        
    def test_option_deletion_cascades_to_votes(self):
        """Test that deleting an option deletes its votes"""
        vote = Vote.objects.create(
            poll=self.poll,
            option=self.option1,
            voter_ip="192.168.1.1"
        )
        
        vote_id = vote.id
        
        # Verify vote exists
        self.assertTrue(Vote.objects.filter(id=vote_id).exists())
        
        # Delete option
        self.option1.delete()
        
        # Verify vote is deleted
        self.assertFalse(Vote.objects.filter(id=vote_id).exists())
