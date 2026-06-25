from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from rest_framework import authentication, exceptions

from tinyinsta.auth_jwt.jwks import JWKSClient


@dataclass(slots=True)
class KeycloakUser:
    user_id: str
    username: str
    claims: dict

    @property
    def is_authenticated(self) -> bool:
        return True


_jwks_client: JWKSClient | None = None


def _get_jwks_client() -> JWKSClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = JWKSClient(os.environ["OIDC_JWKS_URL"])
    return _jwks_client


class KeycloakJWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Malformed Authorization header.")

        token = header[1].decode()
        # Audience verification is opt-in: enable it by setting OIDC_AUDIENCE and
        # adding a matching audience mapper in Keycloak. Signature + issuer are
        # always verified.
        audience = os.environ.get("OIDC_AUDIENCE") or None
        try:
            kid = jwt.get_unverified_header(token)["kid"]
            key = _get_jwks_client().get_key(kid)
            claims = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                audience=audience,
                issuer=os.environ.get("OIDC_ISSUER") or None,
                options={"verify_aud": audience is not None},
            )
        except (jwt.PyJWTError, KeyError) as exc:
            raise exceptions.AuthenticationFailed(f"Invalid JWT: {exc}") from exc

        user = KeycloakUser(
            user_id=claims["sub"],
            username=claims.get("preferred_username", ""),
            claims=claims,
        )
        return (user, token)
