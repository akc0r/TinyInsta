from rest_framework import serializers

from users.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "user_id",
            "username",
            "name",
            "bio",
            "link",
            "avatar_url",
            "created_at",
        ]
        read_only_fields = ["user_id", "created_at"]
