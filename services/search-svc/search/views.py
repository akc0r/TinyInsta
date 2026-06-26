from rest_framework.response import Response
from rest_framework.views import APIView

from search import index


def _limit(request, default: int, cap: int = 50) -> int:
    try:
        return min(int(request.query_params.get("limit", default)), cap)
    except (TypeError, ValueError):
        return default


class Search(APIView):
    """GET /search?q= — combined users + posts search (the search bar)."""

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        return Response(index.search(q, _limit(request, 20)))


class Hashtag(APIView):
    """GET /hashtags/{tag} — posts tagged with a given hashtag."""

    def get(self, request, tag):
        items = index.posts_by_hashtag(tag, _limit(request, 30))
        return Response({"tag": tag.lstrip("#").lower(), "items": items})


class Explore(APIView):
    """GET /explore — popular/recent posts grid."""

    def get(self, request):
        return Response({"items": index.explore(_limit(request, 30))})
