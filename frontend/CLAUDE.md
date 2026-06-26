# CLAUDE.md — frontend/

Next.js **16** (App Router) + React **19** PWA. The client of the TinyInsta microservices:
talks to the API through Traefik and authenticates with Keycloak (OIDC) directly in the browser.

> ⚠️ See `AGENTS.md`: this is Next.js 16 with breaking changes vs. older versions — when unsure
> about an API/convention, check `node_modules/next/dist/docs/` rather than assuming.

## Stack

- **Next.js 16 App Router** + **React 19**, TypeScript.
- **Tailwind CSS v4** (`@tailwindcss/postcss`) + **shadcn/ui** (`components/ui/`, Radix-based),
  Tabler icons, `next-themes` for dark mode.
- **keycloak-js** for auth (OIDC, browser-side token).
- pnpm (workspace). Scripts: `dev`, `build`, `start`, `lint`, `format` (Prettier), `typecheck`.

```bash
pnpm install
pnpm dev        # http://localhost:3000   (or `make front` from repo root)
pnpm typecheck  # tsc --noEmit
pnpm lint
```

## Layout

```
app/                 # App Router routes
├── layout.tsx       # root layout (providers: auth, theme)
├── page.tsx         # home feed (infinite scroll)
├── profile/page.tsx, profile/[userId]/page.tsx
├── upload/page.tsx  # photo/video upload flow
└── globals.css
components/          # feature components (post-card, stories-row, app-shell, *-dialog, ...)
└── ui/              # shadcn/ui primitives — don't hand-edit, regenerate via shadcn
lib/                 # api.ts (fetch + types), auth-context.tsx, keycloak.ts,
│                    # use-timeline.ts (infinite scroll), utils.ts
hooks/               # shared React hooks
```

## Conventions

- **API access** goes through `lib/api.ts`:
  - `apiFetch(path, token, init)` — prefixes `NEXT_PUBLIC_API_URL`, attaches `Bearer <token>`,
    JSON by default. Use for all service calls (via Traefik `/api`).
  - `putToStorage(uploadUrl, file)` — uploads bytes to MinIO via a **presigned URL**; it carries
    its own auth, so **do NOT attach the Bearer token**.
  - Shared response types (`Profile`, `Post`, `Media`, `TimelinePage`, ...) live here — reuse them.
- **Auth**: `lib/auth-context.tsx` exposes `useAuth()` → `{ ready, authenticated, username,
  userId, getToken, login, logout }`. Get the token with `getToken()` and pass it to `apiFetch`.
  `userId` is the Keycloak `sub`. Auth is **client-side** (`"use client"`); there is no server
  session — components needing the token must be client components.
- **Pagination**: home/profile feeds use cursor pagination (`TimelinePage.next_cursor`); the
  infinite-scroll logic is in `lib/use-timeline.ts` — reuse it rather than re-implementing.
- **UI**: compose from `components/ui/` (shadcn) + Tailwind utilities; keep dark-mode support.
  Format with Prettier (`pnpm format`); Tailwind class sorting plugin is enabled.

## Config

`.env.local` (gitignored) — key vars: `NEXT_PUBLIC_API_URL` (Traefik API base) and the
Keycloak client settings consumed by `lib/keycloak.ts`. The browser reaches services through
the gateway, never directly.

## Backend context

The frontend is one piece of a microservices system. For how the API/events/feed work behind it,
see the repo-root `CLAUDE.md`, `services/CLAUDE.md`, and `docs/FRONTEND.md`.
