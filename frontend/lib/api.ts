const API_URL = process.env.NEXT_PUBLIC_API_URL!

export async function apiFetch(
  path: string,
  token: string | undefined,
  init: RequestInit = {},
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
export async function putToStorage(uploadUrl: string, file: File): Promise<Response> {
  return fetch(uploadUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type || "application/octet-stream" },
  })
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
