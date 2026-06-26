# Frontend

A **Next.js** Progressive Web App: the client of the TinyInsta microservices. It talks to the
backend through the Traefik gateway and authenticates against Keycloak (OIDC) directly in the
browser. The backend is frontend-agnostic — every interaction goes through the public API and
WebSocket contracts, so the client could be replaced without touching the services.

## Stack

- **Next.js 16** (App Router) + **React 19**, TypeScript.
- **Tailwind CSS v4** + **shadcn/ui** (Radix-based primitives), Tabler icons, `next-themes` for dark mode.
- **keycloak-js** for OIDC (Authorization Code + PKCE, browser-side token).
- A singleton **WebSocket** client for real-time updates.
- pnpm; PWA (installable, camera access).

## Key flows

### Camera capture
- `navigator.mediaDevices.getUserMedia` accesses the camera.
- Photo: captured into a `<canvas>`. Video: recorded via `MediaRecorder`.
- Preview, then upload **directly to MinIO** through a presigned URL — the binary never transits
  the backend services.

### Infinite scroll
- An `IntersectionObserver` on a bottom sentinel triggers fetching the next page.
- **Cursor-based** pagination (`next_cursor` returned by hometimeline-svc / usertimeline-svc),
  never offset-based.

### Real-time
- A single WebSocket connection to `realtime-svc`.
- **Optimistic updates** for likes (immediate UI increment) reconciled on the server event
  (`post.liked` carrying `new_count`).

### Auth (Keycloak / OIDC)
- Authorization Code + PKCE via `keycloak-js`.
- The JWT is sent as `Authorization: Bearer` on every call through Traefik; refresh is handled
  client-side.

### Search & explore
- Search bar and explore page backed by `search-svc` (Elasticsearch), with request debouncing and
  autocomplete on users and hashtags.

## Surface

Login and profile (view/edit), upload, the home feed, live likes and comments, the camera capture
with the story bar and viewer, the search and explore pages, and the notification center.

## Notes

- API access is centralized in `lib/api.ts` (`apiFetch` for service calls via Traefik;
  `putToStorage` for presigned MinIO uploads). Shared response types live alongside it.
- Auth state is exposed through `useAuth()`; there is no server session — components needing the
  token are client components.
- For implementation conventions see [`frontend/CLAUDE.md`](../frontend/CLAUDE.md).
