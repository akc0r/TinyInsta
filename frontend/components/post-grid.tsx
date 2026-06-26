"use client"

import { useEffect, useState } from "react"
import { IconHeart, IconMessageCircle } from "@tabler/icons-react"

import { apiFetch, type LikeStatus, type Post } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import type { HydratedPost } from "@/lib/use-timeline"
import { PostDialog } from "@/components/post-dialog"

// The square 3-column media grid shared by the explore and profile pages.
// Clicking a cell opens the post in a dialog; the hover overlay shows live like
// and comment counts (likes from interaction-svc, comments from the post doc).
export function PostGrid({ cells }: { cells: HydratedPost[] }) {
  const { getToken } = useAuth()
  const [selected, setSelected] = useState<HydratedPost | null>(null)
  const [likes, setLikes] = useState<Record<string, number>>({})
  // Comments are seeded from the post payload, then refreshed on dialog close.
  const [comments, setComments] = useState<Record<string, number>>({})

  // Fetch the like count for a post and refresh the comment count from the post
  // doc (both can change while the post is open in the dialog).
  async function refresh(post: Post) {
    const token = getToken()
    const [likeRes, postRes] = await Promise.all([
      apiFetch(`/interactions/posts/${post.post_id}/likes`, token),
      apiFetch(`/posts?ids=${post.post_id}`, token),
    ])
    if (likeRes.ok) {
      const data: LikeStatus = await likeRes.json()
      setLikes((m) => ({ ...m, [post.post_id]: data.count }))
    }
    if (postRes.ok) {
      const { items }: { items: Post[] } = await postRes.json()
      if (items[0]) {
        setComments((m) => ({ ...m, [post.post_id]: items[0].comment_count }))
      }
    }
  }

  // Seed comment counts from the cells and fetch each post's like count.
  useEffect(() => {
    setComments(
      Object.fromEntries(cells.map((c) => [c.post.post_id, c.post.comment_count]))
    )
    let cancelled = false
    const token = getToken()
    Promise.all(
      cells.map(async (c) => {
        const r = await apiFetch(
          `/interactions/posts/${c.post.post_id}/likes`,
          token
        )
        return r.ok ? [c.post.post_id, ((await r.json()) as LikeStatus).count] : null
      })
    ).then((pairs) => {
      if (cancelled) return
      setLikes(Object.fromEntries(pairs.filter(Boolean) as [string, number][]))
    })
    return () => {
      cancelled = true
    }
  }, [cells, getToken])

  return (
    <>
      <div className="grid grid-cols-3 gap-1">
        {cells.map((cell) => {
          const { post, imageUrl } = cell
          return (
            <button
              key={post.post_id}
              type="button"
              onClick={() => setSelected(cell)}
              className="group relative aspect-square overflow-hidden bg-muted"
            >
              {imageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={imageUrl}
                  alt={post.caption}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center p-3 text-center text-xs text-muted-foreground">
                  {post.caption || "Post"}
                </div>
              )}
              <div className="absolute inset-0 hidden items-center justify-center gap-6 bg-black/30 text-sm font-semibold text-white group-hover:flex">
                <span className="flex items-center gap-1.5">
                  <IconHeart className="size-5 fill-white" /> {likes[post.post_id] ?? 0}
                </span>
                <span className="flex items-center gap-1.5">
                  <IconMessageCircle className="size-5 fill-white" />{" "}
                  {comments[post.post_id] ?? 0}
                </span>
              </div>
            </button>
          )
        })}
      </div>

      <PostDialog
        post={selected?.post ?? null}
        imageUrl={selected?.imageUrl ?? null}
        open={!!selected}
        onOpenChange={(open) => {
          if (!open && selected) {
            refresh(selected.post) // sync counts changed inside the dialog
            setSelected(null)
          }
        }}
      />
    </>
  )
}
