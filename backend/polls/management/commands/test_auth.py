"""
Management command to test JWT authentication and rate limiting functionality.
"""

import json
import time

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test JWT authentication and rate limiting functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            default="http://localhost:8000",
            help="API host URL (default: http://localhost:8000)",
        )
        parser.add_argument(
            "--username",
            default="testuser",
            help="Username for testing (default: testuser)",
        )
        parser.add_argument(
            "--email",
            default="test@example.com",
            help="Email for test user (default: test@example.com)",
        )
        parser.add_argument(
            "--password",
            default="testpass123",
            help="Password for test user (default: testpass123)",
        )

    def handle(self, *args, **options):
        host = options["host"]
        username = options["username"]
        email = options["email"]
        password = options["password"]

        self.stdout.write(
            self.style.SUCCESS(
                f"\n=== Testing JWT Authentication and Rate Limiting ===\n"
                f"Host: {host}\n"
                f"Username: {username}\n"
            )
        )

        # Step 1: Create test user if doesn't exist
        self.create_test_user(username, email, password)

        # Step 2: Test JWT token authentication
        access_token = self.test_jwt_auth(host, username, password)

        if access_token:
            # Step 3: Test authenticated poll creation with rate limiting
            self.test_poll_creation_rate_limit(host, access_token)

            # Step 4: Test voting rate limiting
            self.test_voting_rate_limit(host)

            # Step 5: Test token refresh
            self.test_token_refresh(host, username, password)

        self.stdout.write(
            self.style.SUCCESS(
                "\n=== Test Completed ===\n"
                "Check the output above for any errors or rate limiting responses."
            )
        )

    def create_test_user(self, username, email, password):
        """Create test user if doesn't exist."""
        try:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email}
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created test user: {username}")
                )
            else:
                # Update password in case it changed
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.WARNING(f"⚠ Using existing user: {username}")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error creating user: {e}"))

    def test_jwt_auth(self, host, username, password):
        """Test JWT token authentication."""
        self.stdout.write("\n--- Testing JWT Authentication ---")

        try:
            # Get JWT token
            response = requests.post(
                f"{host}/api/auth/token/",
                data={"username": username, "password": password},
            )

            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access")
                refresh_token = data.get("refresh")

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ JWT Token obtained successfully\n"
                        f"  Access Token: {access_token[:50]}...\n"
                        f"  Refresh Token: {refresh_token[:50]}..."
                    )
                )

                # Verify token
                verify_response = requests.post(
                    f"{host}/api/auth/token/verify/", data={"token": access_token}
                )

                if verify_response.status_code == 200:
                    self.stdout.write(
                        self.style.SUCCESS("✓ Token verification successful")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ Token verification failed: {verify_response.text}"
                        )
                    )

                return access_token
            else:
                self.stdout.write(
                    self.style.ERROR(f"✗ JWT Authentication failed: {response.text}")
                )
                return None

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Error during JWT authentication: {e}")
            )
            return None

    def test_poll_creation_rate_limit(self, host, access_token):
        """Test poll creation rate limiting (5 per hour)."""
        self.stdout.write("\n--- Testing Poll Creation Rate Limiting ---")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Try creating multiple polls to test rate limiting
        for i in range(7):  # Try 7 polls (should hit limit at 6th)
            poll_data = {
                "title": f"Test Poll {i+1} - {int(time.time())}",
                "description": f"This is test poll number {i+1}",
                "options": [f"Option A {i+1}", f"Option B {i+1}", f"Option C {i+1}"],
                "is_active": True,
            }

            try:
                response = requests.post(
                    f"{host}/api/polls/", headers=headers, data=json.dumps(poll_data)
                )

                if response.status_code == 201:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Poll {i+1} created successfully")
                    )
                elif response.status_code == 429:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ Poll {i+1} blocked by rate limit (429) - This is expected!"
                        )
                    )
                    break
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ Poll {i+1} creation failed: {response.status_code} - {response.text}"
                        )
                    )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error creating poll {i+1}: {e}"))

            # Small delay between requests
            time.sleep(0.1)

    def test_voting_rate_limit(self, host):
        """Test voting rate limiting (10 per minute)."""
        self.stdout.write("\n--- Testing Voting Rate Limiting ---")

        try:
            # First, get a poll to vote on
            response = requests.get(f"{host}/api/polls/")
            if response.status_code == 200:
                polls = response.json()
                if polls:
                    poll_id = polls[0]["id"]
                    option_id = polls[0]["options"][0]["id"]

                    self.stdout.write(f"Testing votes on poll {poll_id}")

                    # Try voting multiple times rapidly (should hit rate limit)
                    for i in range(12):  # Try 12 votes (should hit limit at 11th)
                        vote_data = {"option_id": option_id}

                        try:
                            vote_response = requests.post(
                                f"{host}/api/polls/{poll_id}/vote/",
                                data=json.dumps(vote_data),
                                headers={"Content-Type": "application/json"},
                            )

                            if vote_response.status_code == 200:
                                self.stdout.write(
                                    self.style.SUCCESS(f"✓ Vote {i+1} successful")
                                )
                            elif vote_response.status_code == 400:
                                # Expected after first vote (duplicate vote)
                                if "already voted" in vote_response.text:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"⚠ Vote {i+1} rejected - Already voted (expected)"
                                        )
                                    )
                                else:
                                    self.stdout.write(
                                        self.style.ERROR(
                                            f"✗ Vote {i+1} failed: {vote_response.text}"
                                        )
                                    )
                            elif vote_response.status_code == 429:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"⚠ Vote {i+1} blocked by rate limit (429) - This is expected!"
                                    )
                                )
                                break
                            else:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"✗ Vote {i+1} unexpected response: {vote_response.status_code}"
                                    )
                                )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"✗ Error with vote {i+1}: {e}")
                            )

                        # Small delay between votes
                        time.sleep(0.1)
                else:
                    self.stdout.write(
                        self.style.WARNING("⚠ No polls available for voting test")
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f"✗ Could not fetch polls: {response.text}")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error during voting test: {e}"))

    def test_token_refresh(self, host, username, password):
        """Test JWT token refresh functionality."""
        self.stdout.write("\n--- Testing JWT Token Refresh ---")

        try:
            # Get fresh tokens
            response = requests.post(
                f"{host}/api/auth/token/",
                data={"username": username, "password": password},
            )

            if response.status_code == 200:
                data = response.json()
                refresh_token = data.get("refresh")

                # Test token refresh
                refresh_response = requests.post(
                    f"{host}/api/auth/token/refresh/", data={"refresh": refresh_token}
                )

                if refresh_response.status_code == 200:
                    new_data = refresh_response.json()
                    new_access_token = new_data.get("access")

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Token refresh successful\n"
                            f"  New Access Token: {new_access_token[:50]}..."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ Token refresh failed: {refresh_response.text}"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f"✗ Could not get initial token: {response.text}")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Error during token refresh test: {e}")
            )
