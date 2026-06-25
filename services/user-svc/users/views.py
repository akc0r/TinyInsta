from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Profile
from users.provisioning import get_or_create_profile
from users.serializers import ProfileSerializer


class Me(APIView):
    def get(self, request):
        profile, _ = get_or_create_profile(request.user)
        return Response(ProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = get_or_create_profile(request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfileDetail(APIView):
    def get(self, request, user_id):
        try:
            profile = Profile.objects.get(user_id=user_id)
        except Profile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ProfileSerializer(profile).data)


# --- Social graph (Phase 3) -------------------------------------------------
class Follow(APIView):
    def post(self, request, user_id):
        raise NotImplementedError

    def delete(self, request, user_id):
        raise NotImplementedError


class Followers(APIView):
    def get(self, request, user_id):
        raise NotImplementedError


class Following(APIView):
    def get(self, request, user_id):
        raise NotImplementedError


class Suggestions(APIView):
    def get(self, request):
        raise NotImplementedError
