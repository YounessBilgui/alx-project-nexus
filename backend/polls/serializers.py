from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Poll, PollOption, Vote


class PollOptionSerializer(serializers.ModelSerializer):
    """Serializer for PollOption model."""

    class Meta:
        model = PollOption
        fields = ["id", "text", "vote_count"]


class PollOptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PollOption."""

    class Meta:
        model = PollOption
        fields = ["text"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class PollSerializer(serializers.ModelSerializer):
    """Serializer for Poll model with read operations."""

    options = PollOptionSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    total_votes = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Poll
        fields = [
            "id",
            "title",
            "description",
            "created_by",
            "created_at",
            "expires_at",
            "is_active",
            "options",
            "total_votes",
            "is_expired",
        ]

    def get_total_votes(self, obj):
        """Calculate total votes for the poll."""
        return obj.total_votes


class PollCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating polls with options."""

    options = PollOptionCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Poll
        fields = ["title", "description", "expires_at", "options"]

    def create(self, validated_data):
        """Create poll with options."""
        options_data = validated_data.pop("options")

        # Set the creator from the request context
        validated_data["created_by"] = self.context["request"].user

        poll = Poll.objects.create(**validated_data)

        # Create options for the poll
        for option_data in options_data:
            PollOption.objects.create(poll=poll, **option_data)

        return poll


class VoteSerializer(serializers.Serializer):
    """Serializer for voting on a poll option."""

    option_id = serializers.IntegerField()

    def validate_option_id(self, value):
        """Validate that the option exists and belongs to the poll."""
        poll_id = self.context.get("poll_id")

        try:
            option = PollOption.objects.get(id=value, poll_id=poll_id)
        except PollOption.DoesNotExist:
            raise serializers.ValidationError("Invalid option for this poll.")

        return value


class PollResultSerializer(serializers.ModelSerializer):
    """Serializer for poll results with vote percentages."""

    options = serializers.SerializerMethodField()
    total_votes = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = [
            "id",
            "title",
            "description",
            "total_votes",
            "options",
            "created_at",
            "expires_at",
        ]

    def get_total_votes(self, obj):
        """Get total votes for the poll."""
        return obj.total_votes

    def get_options(self, obj):
        """Get options with vote counts and percentages."""
        total_votes = obj.total_votes
        options_data = []

        for option in obj.options.all():
            percentage = (
                (option.vote_count / total_votes * 100) if total_votes > 0 else 0
            )
            options_data.append(
                {
                    "id": option.id,
                    "text": option.text,
                    "vote_count": option.vote_count,
                    "percentage": round(percentage, 2),
                }
            )

        return options_data
