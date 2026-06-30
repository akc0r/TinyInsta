"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import {
  apiFetch,
  type Media,
  type Post,
  type Profile,
  type TimelinePage,
} from "@/lib/api"
import { useAuth } from "@/lib/auth-context"

export type HydratedPost = { post: Post; imageUrl: string | null }

// A home-feed cell also carries its author, since the home timeline mixes posts
// from every account the viewer follows (unlike a single-author profile grid).
export type FeedCell = HydratedPost & { author: Profile | null }

// Resolve the first media of a post to a displayable image URL (null if none).
async function firstImageUrl(
  post: Post,
  token: string | undefined
): Promise<string | null> {
  const mediaId = post.media_ids[0]
  if (!mediaId) return null
  const res = await apiFetch(`/media/${mediaId}`, token)
  return res.ok ? ((await res.json()) as Media).original_url : null
}

// Hydrate a bare list of post ids into displayable cells: fetch the posts from
// post-svc (the source of truth for media), resolve each first image, and keep
// the input order. Used by the explore grid and hashtag pages, whose ids come
// from the search read model (which doesn't store media).
export async function hydratePostIds(
  ids: string[],
  token: string | undefined
): Promise<HydratedPost[]> {
  if (ids.length === 0) return []
  const postsRes = await apiFetch(`/posts?ids=${ids.join(",")}`, token)
  if (!postsRes.ok) throw new Error(`posts ${postsRes.status}`)
  const { items: posts }: { items: Post[] } = await postsRes.json()
  const rank = new Map(ids.map((id, i) => [id, i]))
  posts.sort((a, b) => (rank.get(a.post_id) ?? 0) - (rank.get(b.post_id) ?? 0))
  return hydratePosts(posts, token)
}

// Resolve each post's first media to a displayable cell, preserving order. Used
// when the caller already holds the full posts (e.g. the tagged grid).
export async function hydratePosts(
  posts: Post[],
  token: string | undefined
): Promise<HydratedPost[]> {
  return Promise.all(
    posts.map(async (post) => ({
      post,
      imageUrl: await firstImageUrl(post, token),
    }))
  )
}

// Fetch a per-author timeline (post ids), hydrate the posts and their first
// media, and expose cursor-based pagination. Shared by the home feed and the
// profile grid.
export function useTimeline(authorId: string | undefined, pageSize = 9) {
  const { getToken } = useAuth()
  const [cells, setCells] = useState<HydratedPost[]>([])
  const [cursor, setCursor] = useState<number | null>(null)
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const inFlight = useRef(false)
  // Bumped on every reset (author change / Strict Mode remount). A request
  // tags itself with the current value and discards its result if the value
  // changed while it was in flight — prevents a stale fetch from appending.
  const gen = useRef(0)

  const loadMore = useCallback(async () => {
    if (!authorId || inFlight.current || done) return
    inFlight.current = true
    const myGen = gen.current
    setLoading(true)
    try {
      const token = getToken()
      const qs = new URLSearchParams({ limit: String(pageSize) })
      if (cursor !== null) qs.set("cursor", String(cursor))
      const tlRes = await apiFetch(`/usertimeline/${authorId}?${qs}`, token)
      if (!tlRes.ok) throw new Error(`usertimeline ${tlRes.status}`)
      const tl: TimelinePage = await tlRes.json()

      let hydrated: HydratedPost[] = []
      if (tl.items.length > 0) {
        const postsRes = await apiFetch(
          `/posts?ids=${tl.items.join(",")}`,
          token
        )
        if (!postsRes.ok) throw new Error(`posts ${postsRes.status}`)
        const { items: posts }: { items: Post[] } = await postsRes.json()

        hydrated = await Promise.all(
          posts.map(async (post) => {
            const mediaId = post.media_ids[0]
            let imageUrl: string | null = null
            if (mediaId) {
              const mRes = await apiFetch(`/media/${mediaId}`, token)
              if (mRes.ok)
                imageUrl = ((await mRes.json()) as Media).original_url
            }
            return { post, imageUrl }
          })
        )
      }

      if (myGen !== gen.current) return // a reset happened; drop this result

      if (hydrated.length > 0) {
        setCells((prev) => {
          const seen = new Set(prev.map((c) => c.post.post_id))
          return [...prev, ...hydrated.filter((c) => !seen.has(c.post.post_id))]
        })
      }
      setCursor(tl.next_cursor)
      if (tl.next_cursor === null) setDone(true)
    } catch (err) {
      if (myGen === gen.current) {
        setError((err as Error).message)
        setDone(true)
      }
    } finally {
      if (myGen === gen.current) {
        inFlight.current = false
        setLoading(false)
      }
    }
  }, [authorId, cursor, done, getToken, pageSize])

  // First page (and reset when the author changes).
  useEffect(() => {
    gen.current += 1
    inFlight.current = false
    // Reset the accumulated pages when the author changes, then refetch page one.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCells([])
    setCursor(null)
    setDone(false)
    setError("")
    loadMore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authorId])

  return { cells, loading, done, error, loadMore }
}

// Fetch the viewer's home timeline (the fan-out feed from hometimeline-svc),
// hydrating each post, its first image, and its author profile. Authors are
// cached across pages so a prolific account is only fetched once.
export function useHomeTimeline(enabled: boolean, pageSize = 5) {
  const { getToken } = useAuth()
  const [cells, setCells] = useState<FeedCell[]>([])
  const [cursor, setCursor] = useState<number | null>(null)
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const inFlight = useRef(false)
  const authors = useRef<Map<string, Profile>>(new Map())

  const loadMore = useCallback(async () => {
    if (!enabled || inFlight.current || done) return
    inFlight.current = true
    setLoading(true)
    try {
      const token = getToken()
      const qs = new URLSearchParams({ limit: String(pageSize) })
      if (cursor !== null) qs.set("cursor", String(cursor))
      const feedRes = await apiFetch(`/home?${qs}`, token)
      if (!feedRes.ok) throw new Error(`home ${feedRes.status}`)
      const feed: TimelinePage = await feedRes.json()

      let hydrated: FeedCell[] = []
      if (feed.items.length > 0) {
        const postsRes = await apiFetch(
          `/posts?ids=${feed.items.join(",")}`,
          token
        )
        if (!postsRes.ok) throw new Error(`posts ${postsRes.status}`)
        const { items: posts }: { items: Post[] } = await postsRes.json()

        // Fetch any author profiles we haven't seen yet, then read from cache.
        const missing = [...new Set(posts.map((p) => p.author_id))].filter(
          (id) => !authors.current.has(id)
        )
        await Promise.all(
          missing.map(async (id) => {
            const r = await apiFetch(`/users/${id}`, token)
            if (r.ok) authors.current.set(id, (await r.json()) as Profile)
          })
        )

        // Keep the server's ordering: posts come back unordered, so re-sort by
        // the post-id order the timeline gave us.
        const rank = new Map(feed.items.map((id, i) => [id, i]))
        posts.sort(
          (a, b) => (rank.get(a.post_id) ?? 0) - (rank.get(b.post_id) ?? 0)
        )

        hydrated = await Promise.all(
          posts.map(async (post) => ({
            post,
            imageUrl: await firstImageUrl(post, token),
            author: authors.current.get(post.author_id) ?? null,
          }))
        )
      }

      if (hydrated.length > 0) {
        setCells((prev) => {
          const seen = new Set(prev.map((c) => c.post.post_id))
          return [...prev, ...hydrated.filter((c) => !seen.has(c.post.post_id))]
        })
      }
      setCursor(feed.next_cursor)
      if (feed.next_cursor === null) setDone(true)
    } catch (err) {
      setError((err as Error).message)
      setDone(true)
    } finally {
      inFlight.current = false
      setLoading(false)
    }
  }, [enabled, cursor, done, getToken, pageSize])

  // First page, once enabled (auth ready).
  useEffect(() => {
    if (enabled) loadMore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])

  return { cells, loading, done, error, loadMore }
}

// Attach an IntersectionObserver to a sentinel that triggers `loadMore`.
export function useInfiniteScroll(loadMore: () => void) {
  const sentinel = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    const node = sentinel.current
    if (!node) return
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) loadMore()
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [loadMore])
  return sentinel
}
