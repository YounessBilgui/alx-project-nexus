from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Poll(models.Model):
    """
    Model representing a poll with multiple options.
    """

    title = models.CharField(max_length=200, help_text="Title of the poll")
    description = models.TextField(
        blank=True, help_text="Detailed description of the poll"
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="polls")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When this poll expires")
    is_active = models.BooleanField(
        default=True, help_text="Whether the poll is active"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        """Check if the poll has expired."""
        return timezone.now() > self.expires_at

    @property
    def total_votes(self):
        """Calculate total votes across all options."""
        return sum(option.vote_count for option in self.options.all())


class PollOption(models.Model):
    """
    Model representing an option within a poll.
    """

    poll = models.ForeignKey(Poll, related_name="options", on_delete=models.CASCADE)
    text = models.CharField(max_length=200, help_text="Option text")
    vote_count = models.PositiveIntegerField(
        default=0, help_text="Number of votes for this option"
    )

    class Meta:
        indexes = [
            models.Index(fields=["poll"]),
        ]

    def __str__(self):
        return f"{self.poll.title} - {self.text}"


class Vote(models.Model):
    """
    Model representing a single vote for a poll option.
    """

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(
        PollOption, on_delete=models.CASCADE, related_name="votes"
    )
    voter_ip = models.GenericIPAddressField(help_text="IP address of the voter")
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("poll", "voter_ip")  # Prevent duplicate voting
        indexes = [
            models.Index(fields=["poll", "voter_ip"]),
            models.Index(fields=["voted_at"]),
        ]

    def __str__(self):
        return f"Vote for {self.option.text} in {self.poll.title}"
