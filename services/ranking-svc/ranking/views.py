from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ranking import store


class Score(APIView):
    """Score a batch of candidate posts for a viewer.

    POST { "viewer_id": "...", "items": ["post_id", ...] }
      → { "scores": {post_id: float}, "ranked": [post_id sorted desc] }

    Internal endpoint (no Traefik route), called server-to-server by hometimeline-svc.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        items = request.data.get("items") or []
        viewer_id = request.data.get("viewer_id") or ""
        if not isinstance(items, list):
            return Response(
                {"detail": "items must be a list of post ids."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        scores = store.score_many(str(viewer_id), [str(i) for i in items])
        ranked = sorted(scores, key=lambda pid: scores[pid], reverse=True)
        return Response({"scores": scores, "ranked": ranked})
