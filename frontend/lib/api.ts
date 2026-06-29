const API_URL = process.env.NEXT_PUBLIC_API_URL!

export async function apiFetch(
  path: string,
  token: string | undefined,
  init: RequestInit = {}
): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  })
}

// Upload bytes straight to object storage. The presigned URL carries its own
// auth, so we must NOT attach the Bearer token here.
export async function putToStorage(
  uploadUrl: string,
  file: File
): Promise<Response> {
  return fetch(uploadUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type || "application/octet-stream" },
  })
}

// The full presigned upload dance: ask media-svc for a URL, PUT the bytes to
// storage, then register the media. Returns the new media id (resolve it to a
// URL later via GET /media/{id}). Shared by the post and story flows.
export async function uploadMedia(
  token: string | undefined,
  file: File,
  kind = "image"
): Promise<string> {
  const ticketRes = await apiFetch("/media/upload-url", token, {
    method: "POST",
    body: JSON.stringify({ kind }),
  })
  if (!ticketRes.ok) throw new Error(`upload-url ${ticketRes.status}`)
  const ticket: UploadTicket = await ticketRes.json()

  const putRes = await putToStorage(ticket.upload_url, file)
  if (!putRes.ok) throw new Error(`storage PUT ${putRes.status}`)

  const mediaRes = await apiFetch("/media", token, {
    method: "POST",
    body: JSON.stringify({ media_id: ticket.media_id, kind }),
  })
  if (!mediaRes.ok) throw new Error(`media ${mediaRes.status}`)
  return ticket.media_id
}

export type Profile = {
  user_id: string
  username: string
  name: string
  bio: string
  link: string
  avatar_url: string
  created_at: string
  // Graph-derived (user-svc Phase 3); absent on list endpoints.
  followers?: number
  following?: number
  is_following?: boolean
  // Viewer ↔ profile relationship (only on the detail endpoint, not on self).
  is_blocking?: boolean
  is_close_friend?: boolean
}

// A suggestion is a profile plus the number of mutual connections.
export type Suggestion = Profile & { mutual: number }

export type UploadTicket = {
  media_id: string
  upload_url: string
  object_url: string
}

export type Post = {
  post_id: string
  author_id: string
  caption: string
  hashtags: string[]
  media_ids: string[]
  comment_count: number
  created_at: string
  // Phase: reels + reposts (optional so older callers stay valid).
  kind?: "post" | "reel"
  mentions?: string[]
  media_variants?: Record<string, Record<string, string>>
  repost_count?: number
}

export type ReelsPage = {
  items: Post[]
  next_cursor: string | null
}

// A saved post (bookmark) as returned by post-svc.
export type SavedItem = {
  post_id: string
  collection: string
  created_at: string
}

export type Media = {
  media_id: string
  owner_id: string
  kind: string
  status: string
  original_url: string
  variants: Record<string, string>
  created_at: string
}

export type TimelinePage = {
  items: string[]
  next_cursor: number | null
}

export type StoryAudience = "public" | "close_friends"

// One ephemeral story. `viewed` is relative to the requesting viewer.
export type Story = {
  story_id: string
  author_id: string
  media_id: string
  audience: StoryAudience
  created_at: string
  expires_at: string
  viewed: boolean
}

// The story bar groups active stories by author; `has_unseen` drives the ring.
export type StoryGroup = {
  author_id: string
  stories: Story[]
  has_unseen: boolean
}

// search-svc read model (Elasticsearch). Hits are projections of events, so a
// post hit carries no media_ids — resolve those from post-svc when hydrating.
export type UserHit = {
  user_id: string
  username: string
  bio: string
}

export type PostHit = {
  post_id: string
  author_id: string
  caption: string
  hashtags: string[]
  created_at: string
}

export type SearchResults = { users: UserHit[]; posts: PostHit[] }

export type HashtagPage = { tag: string; items: PostHit[] }

export type LikeStatus = {
  post_id: string
  count: number
  liked: boolean
}

export type Comment = {
  comment_id: string
  author_id: string
  body: string
  parent_id?: string | null
  edited?: boolean
  created_at: string
}

export type Notification = {
  id: string
  notification_type: "like" | "comment" | "follow" | "mention" | "repost"
  payload: Record<string, string>
  read: boolean
  created_at: string
}

// --- Direct messages (messaging-svc / Cassandra) ---------------------------
export type Conversation = {
  conversation_id: string
  peer_id: string
  last_message: string
  last_message_at: string | null
}

export type Message = {
  message_id: string
  sender_id: string
  recipient_id: string
  body: string
  created_at: string
}

export type MessagePage = {
  items: Message[]
  next_cursor: string | null
}

// The realtime gateway lives at /ws (not behind the /api prefix). Prefer the
// explicit env var, otherwise derive it from the API base.
export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ??
  API_URL.replace(/\/api\/?$/, "/ws").replace(/^http/, "ws")
