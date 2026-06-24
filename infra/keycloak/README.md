# Keycloak — TinyInsta realm

Keycloak is the identity authority (OIDC). On startup, the container **imports** the realm
from `tinyinsta-realm.json` (mounted into `/opt/keycloak/data/import`).

## To configure
- **Realm** `tinyinsta`.
- **Public client** `tinyinsta-frontend`: Authorization Code + PKCE, redirect URIs
  `http://localhost:3000/*`, web origins `+`.
- Mappers: `preferred_username` in the token (standard by default).

The provided `tinyinsta-realm.json` is a **minimal skeleton** — complete it through the console
(`http://localhost:8080`, admin/admin) and re-export:

```bash
docker compose exec keycloak \
  /opt/keycloak/bin/kc.sh export --dir /opt/keycloak/data/import --realm tinyinsta
```

## Validation on the service side
Each service validates JWTs against the realm's **JWKS**:
`http://keycloak:8080/realms/tinyinsta/protocol/openid-connect/certs`
(`OIDC_JWKS_URL` variable). See `libs/tinyinsta/auth_jwt`.
