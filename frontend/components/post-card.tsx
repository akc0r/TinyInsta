"use client"

import Link from "next/link"
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react"
import {
  IconBookmark,
  IconBookmarkFilled,
  IconDots,
  IconHeart,
  IconHeartFilled,
  IconMessageCircle,
  IconRepeat,
  IconSend,
  IconTrash,
} from "@tabler/icons-react"

import {
  apiFetch,
  type Comment,
  type LikeStatus,
  type Post,
  type Profile,
} from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { usePostRealtime } from "@/lib/use-realtime"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { RichText } from "@/components/rich-text"
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"

function timeAgo(iso: string): string {
  const s = Math.max(
    1,
    Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  )
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h`
  return `${Math.floor(s / 86400)}d`
}

// ---------------------------------------------------------------------------
// Shared author-username cache (module-scoped so all PostCard instances share
// it within the same page). Maps author_id → username.
// ---------------------------------------------------------------------------
const usernameCache = new Map<string, string>()
const inflight = new Map<string, Promise<string>>()

async function resolveUsername(
  authorId: string,
  token: string | undefined
): Promise<string> {
  const cached = usernameCache.get(authorId)
  if (cached) return cached

  // Deduplicate concurrent requests for the same author.
  let p = inflight.get(authorId)
  if (!p) {
    p = apiFetch(`/users/${authorId}`, token)
      .then(async (r) => {
        if (!r.ok) return authorId.slice(0, 8)
        const profile: Profile = await r.json()
        const name = profile.username || authorId.slice(0, 8)
        usernameCache.set(authorId, name)
        return name
      })
      .catch(() => authorId.slice(0, 8))
      .finally(() => inflight.delete(authorId))
    inflight.set(authorId, p)
  }
  return p
}

// ---------------------------------------------------------------------------
// The viewer's set of saved post ids, loaded once and shared across all cards
// so the bookmark reflects what's persisted. Mutated in place on save/unsave.
// ---------------------------------------------------------------------------
let savedSetPromise: Promise<Set<string>> | null = null

function loadSavedSet(token: string | undefined): Promise<Set<string>> {
  if (!savedSetPromise) {
    savedSetPromise = apiFetch("/posts/saves", token)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then(
        (d: { items: { post_id: string }[] }) =>
          new Set(d.items.map((s) => s.post_id))
      )
      .catch(() => new Set<string>())
  }
  return savedSetPromise
}

// ---------------------------------------------------------------------------
// Hook: useIsMobile  –  true when viewport width < 640px (sm breakpoint).
// ---------------------------------------------------------------------------
function useIsMobile() {
  const [mobile, setMobile] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 639px)")
    const handler = (e: MediaQueryListEvent | MediaQueryList) =>
      setMobile(e.matches)
    handler(mq)
    mq.addEventListener("change", handler as (e: MediaQueryListEvent) => void)
    return () =>
      mq.removeEventListener(
        "change",
        handler as (e: MediaQueryListEvent) => void
      )
  }, [])
  return mobile
}

// ---------------------------------------------------------------------------
// A comment with its author username resolved.
// ---------------------------------------------------------------------------
type ResolvedComment = Comment & { authorName: string }

export type PostCardProps = {
  post: Post
  imageUrl: string | null
  authorName: string
  authorAvatar?: string
}

export function PostCard({
  post,
  imageUrl,
  authorName,
  authorAvatar,
}: PostCardProps) {
  const { getToken, userId } = useAuth()
  const isMobile = useIsMobile()
  const [liked, setLiked] = useState(false)
  const [likeCount, setLikeCount] = useState(0)
  const [comments, setComments] = useState<ResolvedComment[]>([])
  const [commentCount, setCommentCount] = useState(0)
  const [showComments, setShowComments] = useState(false)
  const [captionExpanded, setCaptionExpanded] = useState(false)
  const [draft, setDraft] = useState("")
  const [posting, setPosting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [reposted, setReposted] = useState(false)
  const [repostId, setRepostId] = useState<string | null>(null)
  const [repostCount, setRepostCount] = useState(post.repost_count ?? 0)
  const actionPending = useRef(false)
  const repostPending = useRef(false)
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

  // Initial bookmark state, from the viewer's shared saved set.
  useEffect(() => {
    let active = true
    loadSavedSet(getToken()).then((set) => {
      if (active) setSaved(set.has(post.post_id))
    })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [post.post_id])

  // Resolve comment author ids → usernames.
  const resolveComments = useCallback(
    async (items: Comment[]): Promise<ResolvedComment[]> => {
      const token = getToken()
      return Promise.all(
        items.map(async (c) => ({
          ...c,
          authorName: await resolveUsername(c.author_id, token),
        }))
      )
    },
    [getToken]
  )

  const loadComments = useCallback(async () => {
    const res = await apiFetch(`/posts/${post.post_id}/comments`, getToken())
    if (!res.ok) return
    const { items }: { items: Comment[] } = await res.json()
    const resolved = await resolveComments(items)
    setComments(resolved)
    setCommentCount(resolved.length)
  }, [post.post_id, getToken, resolveComments])

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
        { method: next ? "POST" : "DELETE" }
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
        { method: "POST", body: JSON.stringify({ body }) }
      )
      if (res.ok) {
        const comment: Comment = await res.json()
        const resolved = await resolveComments([comment])
        setComments((prev) => [...prev, ...resolved])
        setCommentCount((n) => n + 1)
        setShowComments(true)
        setDraft("")
      }
    } finally {
      setPosting(false)
    }
  }

  const toggleSave = async () => {
    if (actionPending.current) return
    actionPending.current = true
    const next = !saved
    setSaved(next) // optimistic
    const set = await loadSavedSet(getToken())
    if (next) set.add(post.post_id)
    else set.delete(post.post_id)
    try {
      const res = await apiFetch("/posts/saves", getToken(), {
        method: next ? "POST" : "DELETE",
        body: JSON.stringify({ post_id: post.post_id }),
      })
      if (!res.ok && res.status !== 204) throw new Error()
    } catch {
      setSaved(!next)
      if (next) set.delete(post.post_id)
      else set.add(post.post_id)
    } finally {
      actionPending.current = false
    }
  }

  const toggleRepost = async () => {
    if (repostPending.current) return
    repostPending.current = true
    const next = !reposted
    setReposted(next) // optimistic
    setRepostCount((n) => Math.max(0, n + (next ? 1 : -1)))
    try {
      if (next) {
        const res = await apiFetch("/posts/reposts", getToken(), {
          method: "POST",
          body: JSON.stringify({ post_id: post.post_id }),
        })
        if (!res.ok) throw new Error()
        const data: { repost_id: string } = await res.json()
        setRepostId(data.repost_id)
      } else if (repostId) {
        const res = await apiFetch(`/posts/reposts/${repostId}`, getToken(), {
          method: "DELETE",
        })
        if (!res.ok && res.status !== 204) throw new Error()
        setRepostId(null)
      }
    } catch {
      setReposted(!next)
      setRepostCount((n) => Math.max(0, n + (next ? -1 : 1)))
    } finally {
      repostPending.current = false
    }
  }

  const deleteComment = async (commentId: string) => {
    const res = await apiFetch(
      `/posts/${post.post_id}/comments/${commentId}`,
      getToken(),
      { method: "DELETE" }
    )
    if (res.ok || res.status === 204) {
      setComments((prev) => prev.filter((c) => c.comment_id !== commentId))
      setCommentCount((n) => Math.max(0, n - 1))
    }
  }

  // -----------------------------------------------------------------------
  // Caption: show only first line, with "more" to expand.
  // -----------------------------------------------------------------------
  const firstLine = post.caption?.split("\n")[0] ?? ""
  const hasMore = post.caption
    ? post.caption.includes("\n") || post.caption.length > 120
    : false

  // -----------------------------------------------------------------------
  // Comment list + input (shared between inline and drawer).
  // -----------------------------------------------------------------------
  const commentListAndInput = (
    <>
      <div className="space-y-2">
        {comments.map((c) => (
          <p
            key={c.comment_id}
            className="group flex items-start gap-1 text-sm"
          >
            <span className="flex-1">
              <Link
                href={`/profile/${c.author_id}`}
                className="font-semibold hover:underline"
              >
                {c.authorName}
              </Link>{" "}
              <RichText text={c.body} />
              {c.edited && (
                <span className="ml-1 text-xs text-muted-foreground">
                  (edited)
                </span>
              )}
            </span>
            {userId === c.author_id && (
              <button
                type="button"
                onClick={() => deleteComment(c.comment_id)}
                aria-label="Delete comment"
                className="shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
              >
                <IconTrash className="size-4" />
              </button>
            )}
          </p>
        ))}
        {comments.length === 0 && (
          <p className="py-2 text-xs text-muted-foreground">No comments yet.</p>
        )}
      </div>

      <form className="flex items-center gap-2 pt-2" onSubmit={submitComment}>
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
    </>
  )

  return (
    <article className="border-b pb-3">
      <header className="flex items-center gap-3 py-3">
        <Link
          href={`/profile/${post.author_id}`}
          className="flex items-center gap-3"
        >
          <Avatar className="size-8">
            {authorAvatar && (
              <AvatarImage src={authorAvatar} alt={authorName} />
            )}
            <AvatarFallback>{initial}</AvatarFallback>
          </Avatar>
          <span className="text-sm font-semibold hover:underline">
            {authorName}
          </span>
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
        <Button
          variant="ghost"
          size="icon"
          aria-label="Repost"
          onClick={toggleRepost}
        >
          <IconRepeat
            className={cn("size-6", reposted && "text-green-600")}
            stroke={1.8}
          />
        </Button>
        {repostCount > 0 && (
          <span className="-ml-1 text-sm text-muted-foreground">
            {repostCount}
          </span>
        )}
        <Button variant="ghost" size="icon" aria-label="Share">
          <IconSend className="size-6" stroke={1.8} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto"
          aria-label="Save"
          onClick={toggleSave}
        >
          {saved ? (
            <IconBookmarkFilled className="size-6" />
          ) : (
            <IconBookmark className="size-6" stroke={1.8} />
          )}
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
            {captionExpanded ? (
              <span className="whitespace-pre-line">
                <RichText text={post.caption} />
              </span>
            ) : (
              <>
                <span>
                  <RichText
                    text={
                      firstLine.length > 120
                        ? firstLine.slice(0, 120) + "…"
                        : firstLine
                    }
                  />
                </span>
                {hasMore && (
                  <button
                    type="button"
                    onClick={() => setCaptionExpanded(true)}
                    className="ml-1 text-muted-foreground hover:underline"
                  >
                    more
                  </button>
                )}
              </>
            )}
          </p>
        )}

        {/* Toggle comments button — always visible */}
        <button
          type="button"
          onClick={toggleComments}
          className="text-sm text-muted-foreground hover:underline"
        >
          {showComments
            ? "Hide comments"
            : commentCount > 0
              ? `View all ${commentCount} comment${commentCount === 1 ? "" : "s"}`
              : "Comments"}
        </button>

        {/* Desktop inline comments — hidden on mobile since we use a drawer there */}
        {!isMobile && showComments && (
          <div className="pt-1">
            {commentListAndInput}
            <Separator className="mt-3" />
          </div>
        )}
      </div>

      {/* Mobile drawer for comments */}
      {isMobile && (
        <Drawer open={showComments} onOpenChange={setShowComments}>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>Comments</DrawerTitle>
            </DrawerHeader>
            <ScrollArea className="max-h-[60vh] overflow-y-auto px-4 pb-4">
              {commentListAndInput}
            </ScrollArea>
          </DrawerContent>
        </Drawer>
      )}
    </article>
  )
}
