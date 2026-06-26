from django.urls import include, path
from tinyinsta.service.urls import common_urlpatterns

urlpatterns = common_urlpatterns + [
    path("", include("media.urls")),
]
