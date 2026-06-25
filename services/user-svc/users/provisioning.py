"""Lazy profile provisioning on first authenticated request.

The user_id is the Keycloak `sub`; on first contact we create the profile and
emit `user.created` (best-effort — a bus outage must not break login).
"""

import logging

from tinyinsta.bus import Producer
from tinyinsta.events import types

from users import graph
from users.models import Profile

logger = logging.getLogger(__name__)

_producer = Producer()


def get_or_create_profile(user) -> tuple[Profile, bool]:
    profile, created = Profile.objects.get_or_create(
        user_id=user.user_id,
        defaults={"username": user.username or str(user.user_id)},
    )
    if created:
        try:
            graph.ensure_user(str(profile.user_id))
        except Exception:  # noqa: BLE001 — graph node is created lazily on follow anyway
            logger.warning("failed to create graph node", exc_info=True)
        try:
            _producer.publish(
                types.USER_CREATED,
                {"user_id": str(profile.user_id), "username": profile.username},
                key=str(profile.user_id),
            )
            _producer.flush()
        except Exception:  # noqa: BLE001 — provisioning must not fail on a bus outage
            logger.warning("failed to publish user.created", exc_info=True)
    return profile, created
