"use client"

import Link from "next/link"
import { useState } from "react"
import {
  IconBookmark,
  IconDots,
  IconHeart,
  IconHeartFilled,
  IconMessageCircle,
  IconSend,
} from "@tabler/icons-react"

import type { Post } from "@/lib/api"
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
  const [liked, setLiked] = useState(false)
  const initial = authorName.charAt(0).toUpperCase()

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
            onDoubleClick={() => setLiked(true)}
          />
        )}
      </div>

      <div className="flex items-center gap-1 pt-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setLiked((v) => !v)}
          aria-label="Like"
        >
          {liked ? (
            <IconHeartFilled className="size-6 text-red-500" />
          ) : (
            <IconHeart className="size-6" stroke={1.8} />
          )}
        </Button>
        <Button variant="ghost" size="icon" aria-label="Comment">
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
        <p className="text-sm font-semibold">{liked ? 1 : 0} likes</p>
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
        <p className="text-sm text-muted-foreground">View all comments</p>
      </div>

      <Separator className="mt-3" />
      <form
        className="flex items-center gap-2 pt-1"
        onSubmit={(e) => e.preventDefault()}
      >
        <Input
          placeholder="Add a comment…"
          className="h-8 border-0 px-1 shadow-none focus-visible:ring-0"
        />
        <Button
          type="submit"
          variant="ghost"
          size="sm"
          className={cn("font-semibold text-primary")}
          disabled
        >
          Post
        </Button>
      </form>
    </article>
  )
}
