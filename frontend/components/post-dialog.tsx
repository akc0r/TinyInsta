"use client"

import { useEffect, useState } from "react"

import { apiFetch, type Post, type Profile } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog"
import { PostCard } from "@/components/post-card"

// A post opened in a modal (from the explore / profile grids). Reuses PostCard
// for the full like/comment/realtime behaviour; we only need to resolve the
// author's username and avatar to feed it.
export function PostDialog({
  post,
  imageUrl,
  open,
  onOpenChange,
}: {
  post: Post | null
  imageUrl: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { getToken } = useAuth()
  const [author, setAuthor] = useState<Profile | null>(null)

  useEffect(() => {
    setAuthor(null)
    if (!post) return
    apiFetch(`/users/${post.author_id}`, getToken())
      .then((r) => (r.ok ? r.json() : null))
      .then(setAuthor)
      .catch(() => {})
  }, [post, getToken])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showClose={false}
        className="max-h-[92vh] max-w-[460px] overflow-y-auto p-4"
      >
        <DialogTitle className="sr-only">Post</DialogTitle>
        {post && (
          <PostCard
            post={post}
            imageUrl={imageUrl}
            authorName={author?.username ?? post.author_id.slice(0, 8)}
            authorAvatar={author?.avatar_url}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}
