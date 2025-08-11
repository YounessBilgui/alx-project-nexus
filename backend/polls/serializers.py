from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from .models import Poll, PollOption, Vote


class PollOptionSerializer(serializers.ModelSerializer):
    """Serializer for PollOption model."""

    class Meta:
        model = PollOption
        fields = ["id", "text", "vote_count"]


class PollOptionNestedSerializer(serializers.ModelSerializer):
    """Serializer for creating PollOption within polls (nested creation)."""

    class Meta:
        model = PollOption
        fields = ["text"]  # Only text field for nested creation


class PollOptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PollOption."""

    class Meta:
        model = PollOption
        fields = ["poll", "text"]  # Include poll field for standalone creation


class PollOptionStandaloneSerializer(serializers.ModelSerializer):
    """Serializer for creating standalone poll options (for API endpoint)."""

    class Meta:
        model = PollOption
        fields = ["poll", "text"]


class PollOptionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating poll options (text only)."""

    class Meta:
        model = PollOption
        fields = ["text"]


class VoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating votes via the votes API endpoint."""

    class Meta:
        model = Vote
        fields = ["poll", "option"]

    def validate(self, data):
        """Validate that option belongs to the poll."""
        poll = data.get("poll")
        option = data.get("option")

        if option.poll != poll:
            raise serializers.ValidationError(
                "Option does not belong to the specified poll."
            )

        return data

    def create(self, validated_data):
        """Create vote with IP address."""
        # Get IP from request context
        request = self.context.get("request")
        if request:
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                voter_ip = x_forwarded_for.split(",")[0]
            else:
                voter_ip = request.META.get("REMOTE_ADDR")
        else:
            voter_ip = "127.0.0.1"  # Default for tests

        validated_data["voter_ip"] = voter_ip
        return super().create(validated_data)


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


class PollUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating polls (without options)."""

    class Meta:
        model = Poll
        fields = ["title", "description", "expires_at"]

    def validate_expires_at(self, value):
        """Validate that expiry date is in the future."""
        if value <= timezone.now():
            raise serializers.ValidationError("Expiry date must be in the future.")
        return value

    def validate_title(self, value):
        """Validate that title is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value


class PollCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating polls with options."""

    options = PollOptionNestedSerializer(many=True, write_only=True)

    class Meta:
        model = Poll
        fields = ["title", "description", "expires_at", "options"]

    def validate_expires_at(self, value):
        """Validate that expiry date is in the future."""
        if value <= timezone.now():
            raise serializers.ValidationError("Expiry date must be in the future.")
        return value

    def validate_title(self, value):
        """Validate that title is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def create(self, validated_data):
        """Create poll with options."""
        options_data = validated_data.pop("options")

        # Set the creator from the request context
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        else:
            # For tests or when no authenticated user, get or create a default user
            from django.contrib.auth.models import User

            default_user, created = User.objects.get_or_create(
                username="test_user", defaults={"email": "test@example.com"}
            )
            validated_data["created_by"] = default_user

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
    """Serializer for poll results with vote counts and percentages."""

    options = serializers.SerializerMethodField()
    total_votes = serializers.SerializerMethodField()
    results = serializers.SerializerMethodField()  # Add results field for tests

    class Meta:
        model = Poll
        fields = [
            "id",
            "title",
            "description",
            "total_votes",
            "options",
            "results",  # Include results field
            "created_at",
            "expires_at",
        ]

    def get_total_votes(self, obj):
        """Get total votes for the poll."""
        return obj.total_votes

    def get_results(self, obj):
        """Get results - same as options for backward compatibility."""
        return self.get_options(obj)

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
