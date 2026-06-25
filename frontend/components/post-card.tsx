"use client"

import Link from "next/link"
import { type FormEvent, useEffect, useRef, useState } from "react"
import {
  IconBookmark,
  IconDots,
  IconHeart,
  IconHeartFilled,
  IconMessageCircle,
  IconSend,
} from "@tabler/icons-react"

import { apiFetch, type Comment, type LikeStatus, type Post } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { usePostRealtime } from "@/lib/use-realtime"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"

function timeAgo(iso: string): string {
  const s = Math.max(1, Math.floor((Date.now() - new Date(iso).getTime()) / 1000))
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h`
  return `${Math.floor(s / 86400)}d`
}

export type PostCardProps = {
  post: Post
  imageUrl: string | null
  authorName: string
  authorAvatar?: string
}

export function PostCard({ post, imageUrl, authorName, authorAvatar }: PostCardProps) {
  const { getToken } = useAuth()
  const [liked, setLiked] = useState(false)
  const [likeCount, setLikeCount] = useState(0)
  const [comments, setComments] = useState<Comment[]>([])
  const [commentCount, setCommentCount] = useState(0)
  const [showComments, setShowComments] = useState(false)
  const [draft, setDraft] = useState("")
  const [posting, setPosting] = useState(false)
  const pending = useRef(false)
  const initial = authorName.charAt(0).toUpperCase()

  // Initial like state (count + whether the viewer already liked).
  useEffect(() => {
    apiFetch(`/interactions/posts/${post.post_id}/likes`, getToken())
      .then((r) => (r.ok ? r.json() : null))
      .then((data: LikeStatus | null) => {
        if (!data) return
        setLikeCount(data.count)
        setLiked(data.liked)
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [post.post_id])

  const loadComments = async () => {
    const res = await apiFetch(`/posts/${post.post_id}/comments`, getToken())
    if (!res.ok) return
    const { items }: { items: Comment[] } = await res.json()
    setComments(items)
    setCommentCount(items.length)
  }

  // Live counters pushed from other clients (or our own other devices).
  usePostRealtime(post.post_id, {
    onLiked: (count) => setLikeCount(count),
    onCommented: () => {
      setCommentCount((n) => n + 1)
      if (showComments) loadComments()
    },
  })

  const toggleLike = async (next = !liked) => {
    if (pending.current || next === liked) return
    pending.current = true
    setLiked(next) // optimistic
    setLikeCount((n) => Math.max(0, n + (next ? 1 : -1)))
    try {
      const res = await apiFetch(
        `/interactions/posts/${post.post_id}/like`,
        getToken(),
        { method: next ? "POST" : "DELETE" },
      )
      if (res.ok) {
        const data: LikeStatus = await res.json()
        setLiked(data.liked)
        setLikeCount(data.count)
      }
    } catch {
      setLiked(!next) // revert on failure
    } finally {
      pending.current = false
    }
  }

  const toggleComments = () => {
    const next = !showComments
    setShowComments(next)
    if (next && comments.length === 0) loadComments()
  }

  const submitComment = async (e: FormEvent) => {
    e.preventDefault()
    const body = draft.trim()
    if (!body || posting) return
    setPosting(true)
    try {
      const res = await apiFetch(
        `/posts/${post.post_id}/comments`,
        getToken(),
        { method: "POST", body: JSON.stringify({ body }) },
      )
      if (res.ok) {
        const comment: Comment = await res.json()
        setComments((prev) => [...prev, comment])
        setCommentCount((n) => n + 1)
        setShowComments(true)
        setDraft("")
      }
    } finally {
      setPosting(false)
    }
  }

  return (
    <article className="border-b pb-3">
      <header className="flex items-center gap-3 py-3">
        <Link
          href={`/profile/${post.author_id}`}
          className="flex items-center gap-3"
        >
          <Avatar className="size-8">
            {authorAvatar && <AvatarImage src={authorAvatar} alt={authorName} />}
            <AvatarFallback>{initial}</AvatarFallback>
          </Avatar>
          <span className="text-sm font-semibold hover:underline">{authorName}</span>
        </Link>
        <span className="text-sm text-muted-foreground">
          • {timeAgo(post.created_at)}
        </span>
        <Button variant="ghost" size="icon" className="ml-auto">
          <IconDots className="size-5" />
        </Button>
      </header>

      <div className="overflow-hidden rounded-sm border bg-muted">
        {imageUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={post.caption}
            className="aspect-square w-full object-cover"
            onDoubleClick={() => toggleLike(true)}
          />
        )}
      </div>

      <div className="flex items-center gap-1 pt-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => toggleLike()}
          aria-label="Like"
        >
          {liked ? (
            <IconHeartFilled className="size-6 text-red-500" />
          ) : (
            <IconHeart className="size-6" stroke={1.8} />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Comment"
          onClick={toggleComments}
        >
          <IconMessageCircle className="size-6" stroke={1.8} />
        </Button>
        <Button variant="ghost" size="icon" aria-label="Share">
          <IconSend className="size-6" stroke={1.8} />
        </Button>
        <Button variant="ghost" size="icon" className="ml-auto" aria-label="Save">
          <IconBookmark className="size-6" stroke={1.8} />
        </Button>
      </div>

      <div className="space-y-1 px-1">
        <p className="text-sm font-semibold">
          {likeCount} {likeCount === 1 ? "like" : "likes"}
        </p>
        {post.caption && (
          <p className="text-sm">
            <Link
              href={`/profile/${post.author_id}`}
              className="font-semibold hover:underline"
            >
              {authorName}
            </Link>{" "}
            <span>{post.caption}</span>
          </p>
        )}

        {commentCount > 0 && (
          <button
            type="button"
            onClick={toggleComments}
            className="text-sm text-muted-foreground hover:underline"
          >
            {showComments
              ? "Hide comments"
              : `View all ${commentCount} comment${commentCount === 1 ? "" : "s"}`}
          </button>
        )}

        {showComments &&
          comments.map((c) => (
            <p key={c.comment_id} className="text-sm">
              <Link
                href={`/profile/${c.author_id}`}
                className="font-semibold hover:underline"
              >
                {c.author_id.slice(0, 8)}
              </Link>{" "}
              <span>{c.body}</span>
            </p>
          ))}
      </div>

      <Separator className="mt-3" />
      <form className="flex items-center gap-2 pt-1" onSubmit={submitComment}>
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add a comment…"
          className="h-8 border-0 px-1 shadow-none focus-visible:ring-0"
        />
        <Button
          type="submit"
          variant="ghost"
          size="sm"
          className={cn("font-semibold text-primary")}
          disabled={!draft.trim() || posting}
        >
          Post
        </Button>
      </form>
    </article>
  )
}
