"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { apiFetch, type Media, type Post, type TimelinePage } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"

export type HydratedPost = { post: Post; imageUrl: string | null }

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
        const postsRes = await apiFetch(`/posts?ids=${tl.items.join(",")}`, token)
        if (!postsRes.ok) throw new Error(`posts ${postsRes.status}`)
        const { items: posts }: { items: Post[] } = await postsRes.json()

        hydrated = await Promise.all(
          posts.map(async (post) => {
            const mediaId = post.media_ids[0]
            let imageUrl: string | null = null
            if (mediaId) {
              const mRes = await apiFetch(`/media/${mediaId}`, token)
              if (mRes.ok) imageUrl = ((await mRes.json()) as Media).original_url
            }
            return { post, imageUrl }
          }),
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
    setCells([])
    setCursor(null)
    setDone(false)
    setError("")
    loadMore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authorId])

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
