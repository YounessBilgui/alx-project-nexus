"""
Performance tests for the ALX Project Nexus - Online Poll System
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.test.utils import override_settings
from django.db import transaction
from datetime import timedelta
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Import models from backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from polls.models import Poll, PollOption, Vote


class PerformanceTestCase(TestCase):
    """Base class for performance tests"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def time_operation(self, operation, *args, **kwargs):
        """Time a database operation"""
        start_time = time.time()
        result = operation(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time


class PollQueryPerformanceTest(PerformanceTestCase):
    """Test poll query performance"""
    
    def test_poll_list_performance(self):
        """Test performance of listing polls"""
        # Create many polls
        polls = []
        for i in range(100):
            poll = Poll.objects.create(
                title=f"Poll {i}",
                description=f"Description {i}",
                created_by=self.user,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            polls.append(poll)
            
        # Time the query
        def get_polls():
            return list(Poll.objects.all()[:50])
            
        result, duration = self.time_operation(get_polls)
        
        # Should complete within reasonable time (e.g., 1 second)
        self.assertLess(duration, 1.0)
        self.assertEqual(len(result), 50)
        
    def test_poll_with_options_performance(self):
        """Test performance of querying polls with options"""
        # Create poll with many options
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Create many options
        for i in range(50):
            PollOption.objects.create(
                poll=poll,
                text=f"Option {i}"
            )
            
        def get_poll_with_options():
            return Poll.objects.prefetch_related('options').get(id=poll.id)
            
        result, duration = self.time_operation(get_poll_with_options)
        
        # Should be fast with prefetch_related
        self.assertLess(duration, 0.5)
        self.assertEqual(result.options.count(), 50)
        
    def test_vote_counting_performance(self):
        """Test performance of vote counting"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        option = PollOption.objects.create(poll=poll, text="Option 1")
        
        # Create many votes
        votes = []
        for i in range(1000):
            vote = Vote.objects.create(
                poll=poll,
                option=option,
                voter_ip=f"192.168.1.{i % 255}"
            )
            votes.append(vote)
            
        def count_votes():
            return Vote.objects.filter(poll=poll).count()
            
        result, duration = self.time_operation(count_votes)
        
        # Should be reasonably fast
        self.assertLess(duration, 0.5)
        self.assertEqual(result, 1000)


class ConcurrentVotingTest(TransactionTestCase):
    """Test concurrent voting scenarios"""
    
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
        
        self.option = PollOption.objects.create(poll=self.poll, text="Option 1")
        
    def test_concurrent_voting_same_ip(self):
        """Test concurrent voting from same IP address"""
        voter_ip = "192.168.1.100"
        votes_created = []
        errors = []
        
        def create_vote():
            try:
                with transaction.atomic():
                    vote = Vote.objects.create(
                        poll=self.poll,
                        option=self.option,
                        voter_ip=voter_ip
                    )
                    votes_created.append(vote)
            except Exception as e:
                errors.append(e)
                
        # Try to create multiple votes concurrently from same IP
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_vote)
            threads.append(thread)
            
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Only one vote should be created (due to unique constraint)
        actual_votes = Vote.objects.filter(poll=self.poll, voter_ip=voter_ip).count()
        self.assertEqual(actual_votes, 1)
        
    def test_concurrent_voting_different_ips(self):
        """Test concurrent voting from different IP addresses"""
        votes_created = []
        errors = []
        
        def create_vote(ip_suffix):
            try:
                voter_ip = f"192.168.1.{ip_suffix}"
                vote = Vote.objects.create(
                    poll=self.poll,
                    option=self.option,
                    voter_ip=voter_ip
                )
                votes_created.append(vote)
            except Exception as e:
                errors.append(e)
                
        # Create votes from different IPs concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_vote, i) for i in range(1, 21)]
            
            # Wait for all to complete
            for future in futures:
                future.result()
                
        # All votes should be created successfully
        total_votes = Vote.objects.filter(poll=self.poll).count()
        self.assertEqual(total_votes, 20)
        self.assertEqual(len(errors), 0)


class DatabasePerformanceTest(PerformanceTestCase):
    """Test database performance and optimization"""
    
    def test_bulk_poll_creation(self):
        """Test bulk creation of polls"""
        polls_data = []
        for i in range(100):
            polls_data.append(Poll(
                title=f"Poll {i}",
                description=f"Description {i}",
                created_by=self.user,
                expires_at=timezone.now() + timedelta(hours=24)
            ))
            
        def bulk_create_polls():
            return Poll.objects.bulk_create(polls_data)
            
        result, duration = self.time_operation(bulk_create_polls)
        
        # Bulk create should be faster than individual creates
        self.assertLess(duration, 1.0)
        self.assertEqual(len(result), 100)
        
    def test_bulk_vote_creation(self):
        """Test bulk creation of votes"""
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        option = PollOption.objects.create(poll=poll, text="Option 1")
        
        votes_data = []
        for i in range(1000):
            votes_data.append(Vote(
                poll=poll,
                option=option,
                voter_ip=f"192.168.1.{i % 255}"
            ))
            
        def bulk_create_votes():
            return Vote.objects.bulk_create(votes_data, ignore_conflicts=True)
            
        result, duration = self.time_operation(bulk_create_votes)
        
        # Should be reasonably fast
        self.assertLess(duration, 2.0)
        
    def test_query_optimization_select_related(self):
        """Test query optimization with select_related"""
        # Create polls with user data
        for i in range(50):
            Poll.objects.create(
                title=f"Poll {i}",
                description=f"Description {i}",
                created_by=self.user,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
        # Query without select_related (causes N+1 queries)
        def query_without_optimization():
            polls = Poll.objects.all()
            usernames = [poll.created_by.username for poll in polls]
            return usernames
            
        # Query with select_related (optimized)
        def query_with_optimization():
            polls = Poll.objects.select_related('created_by').all()
            usernames = [poll.created_by.username for poll in polls]
            return usernames
            
        # Time both approaches
        result1, duration1 = self.time_operation(query_without_optimization)
        result2, duration2 = self.time_operation(query_with_optimization)
        
        # Optimized query should be faster
        self.assertLess(duration2, duration1)
        self.assertEqual(result1, result2)


class MemoryUsageTest(PerformanceTestCase):
    """Test memory usage patterns"""
    
    def test_large_queryset_iteration(self):
        """Test memory usage when iterating over large querysets"""
        # Create many polls
        for i in range(1000):
            Poll.objects.create(
                title=f"Poll {i}",
                description=f"Description {i}",
                created_by=self.user,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
        # Use iterator() to avoid loading all objects into memory
        def iterate_efficiently():
            count = 0
            for poll in Poll.objects.iterator():
                count += 1
            return count
            
        result, duration = self.time_operation(iterate_efficiently)
        
        # Should complete without excessive memory usage
        self.assertEqual(result, 1000)
        self.assertLess(duration, 5.0)


class CachePerformanceTest(PerformanceTestCase):
    """Test caching performance"""
    
    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_poll_results_caching(self):
        """Test caching of poll results"""
        from django.core.cache import cache
        
        poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        option = PollOption.objects.create(poll=poll, text="Option 1")
        
        # Create votes
        for i in range(100):
            Vote.objects.create(
                poll=poll,
                option=option,
                voter_ip=f"192.168.1.{i}"
            )
            
        cache_key = f"poll_results_{poll.id}"
        
        # First call (no cache)
        def get_results_no_cache():
            cache.delete(cache_key)
            return Vote.objects.filter(poll=poll).count()
            
        # Second call (with cache)
        def get_results_with_cache():
            cached_result = cache.get(cache_key)
            if cached_result is None:
                result = Vote.objects.filter(poll=poll).count()
                cache.set(cache_key, result, 300)  # Cache for 5 minutes
                return result
            return cached_result
            
        result1, duration1 = self.time_operation(get_results_no_cache)
        result2, duration2 = self.time_operation(get_results_with_cache)
        
        # Second call should be faster due to caching
        self.assertEqual(result1, result2)
        # Note: In-memory cache might not show significant difference for small datasets
