"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import {
  apiFetch,
  type Media,
  type Post,
  type Profile,
  type ReelsPage,
} from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { useInfiniteScroll } from "@/lib/use-timeline"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { RichText } from "@/components/rich-text"

type ReelCell = {
  post: Post
  mediaUrl: string | null
  isVideo: boolean
  author: Profile | null
}

export default function ReelsPage() {
  const { ready, authenticated, getToken, login } = useAuth()
  const [cells, setCells] = useState<ReelCell[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)
  const inFlight = useRef(false)
  const authors = useRef<Map<string, Profile>>(new Map())

  const loadMore = useCallback(async () => {
    if (!ready || !authenticated || inFlight.current || done) return
    inFlight.current = true
    setLoading(true)
    try {
      const token = getToken()
      const qs = new URLSearchParams({ limit: "5" })
      if (cursor) qs.set("cursor", cursor)
      const res = await apiFetch(`/posts/reels?${qs}`, token)
      if (!res.ok) throw new Error(`reels ${res.status}`)
      const page: ReelsPage = await res.json()

      const missing = [...new Set(page.items.map((p) => p.author_id))].filter(
        (id) => !authors.current.has(id)
      )
      await Promise.all(
        missing.map(async (id) => {
          const r = await apiFetch(`/users/${id}`, token)
          if (r.ok) authors.current.set(id, (await r.json()) as Profile)
        })
      )

      const hydrated: ReelCell[] = await Promise.all(
        page.items.map(async (post) => {
          let mediaUrl: string | null = null
          let isVideo = false
          const mediaId = post.media_ids[0]
          if (mediaId) {
            const m = await apiFetch(`/media/${mediaId}`, token)
            if (m.ok) {
              const media = (await m.json()) as Media
              mediaUrl = media.variants?.["720p"] ?? media.original_url
              isVideo = media.kind === "video"
            }
          }
          return {
            post,
            mediaUrl,
            isVideo,
            author: authors.current.get(post.author_id) ?? null,
          }
        })
      )

      setCells((prev) => {
        const seen = new Set(prev.map((c) => c.post.post_id))
        return [...prev, ...hydrated.filter((c) => !seen.has(c.post.post_id))]
      })
      setCursor(page.next_cursor)
      if (page.next_cursor === null) setDone(true)
    } catch {
      setDone(true)
    } finally {
      inFlight.current = false
      setLoading(false)
    }
  }, [ready, authenticated, cursor, done, getToken])

  useEffect(() => {
    if (ready && authenticated) loadMore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, authenticated])

  const sentinel = useInfiniteScroll(loadMore)

  if (ready && !authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">Log in to watch reels.</p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[460px] px-4 py-6">
      <h1 className="mb-4 text-xl font-semibold">Reels</h1>
      <div className="space-y-6">
        {cells.map(({ post, mediaUrl, isVideo, author }) => (
          <article
            key={post.post_id}
            className="overflow-hidden rounded-lg border"
          >
            <div className="relative aspect-[9/16] bg-black">
              {mediaUrl &&
                (isVideo ? (
                  <video
                    src={mediaUrl}
                    className="size-full object-cover"
                    controls
                    loop
                    muted
                    playsInline
                  />
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={mediaUrl}
                    alt={post.caption}
                    className="size-full object-cover"
                  />
                ))}
            </div>
            <div className="space-y-1 p-3">
              <p className="text-sm font-semibold">
                {author?.username ?? post.author_id.slice(0, 8)}
              </p>
              {post.caption && (
                <p className="text-sm whitespace-pre-line">
                  <RichText text={post.caption} />
                </p>
              )}
            </div>
          </article>
        ))}

        {loading && <Skeleton className="aspect-[9/16] w-full rounded-lg" />}
        {cells.length === 0 && done && !loading && (
          <p className="py-12 text-center text-sm text-muted-foreground">
            No reels yet. Upload a video to get started.
          </p>
        )}
        <div ref={sentinel} className="h-px" />
      </div>
    </div>
  )
}
