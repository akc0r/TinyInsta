# Frontend

> **Choice: Next.js (React).** On TinyInsta, the value is in the backend (microservices, polyglot persistence, CQRS). The frontend should step aside and let us move fast → the comfort zone wins, and `next/image` + SSR fit the needs of a media app.
>
> **Alternative: Angular.** If the goal becomes building up Angular skills (interviews, market), a switch is possible — since the backend is frontend-agnostic, only this document and the `frontend/` folder change. ⚠️ Mind the trap: on such a backend-heavy project, the frontend tends to be delegated; to genuinely learn Angular, writing it yourself (a tutor, not a generator) and dedicating time to it is non-negotiable. For pure Angular learning, a small 100% frontend project is often more effective.

## Stack

- **Next.js (App Router)** + React, **Tailwind** for styling, **pnpm**.
- **PWA**: installable, camera access.
- A singleton **WebSocket** client for real-time.

## Frontend features

### Camera flow
- `navigator.mediaDevices.getUserMedia` to access the camera.
- Photo: capture into a `<canvas>`. Video: `MediaRecorder`.
- Preview → upload **directly to MinIO** via presigned URL (the binary does not transit through the backend).

### Infinite scroll
- `IntersectionObserver` on a sentinel element at the bottom of the list → fetch the next page.
- **Cursor-based** pagination (`next_cursor` returned by hometimeline-svc / usertimeline-svc), never offset-based.
- Virtualization (react-window) if the item volume requires it.

### Real-time
- A single WebSocket service, connected to `realtime-svc`.
- **Optimistic updates** for likes (immediate UI increment) then **reconciliation** on the server event (`post.liked` with `new_count`).

### Auth (Keycloak / OIDC)
- Authorization Code + PKCE via `keycloak-js` (or NextAuth with the Keycloak provider).
- The obtained JWT is sent as `Authorization: Bearer` on every call through Traefik.
- Refresh token handled on the client.

### Search & explore
- Search bar + explore page wired to `search-svc` (Elasticsearch).
- Request debouncing; autocomplete on users/hashtags.

## Screen breakdown (by phase)

| Phase | Frontend screen(s) |
|---|---|
| 1 | Login, profile page (editing) |
| 2 | Upload, profile grid |
| 3 | Followers/following list, suggestions |
| 4 | **Feed** + infinite scroll |
| 5 | Live likes/comments |
| 6 | Camera capture, story bar + viewer |
| 7 | Search, explore page |
| 9 | Notification center |
