"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { apiFetch, type Profile } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { useHomeTimeline, useInfiniteScroll } from "@/lib/use-timeline"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { PostCard } from "@/components/post-card"
import { RightRail } from "@/components/right-rail"
import { StoriesRow } from "@/components/stories-row"

export default function HomePage() {
  const { ready, authenticated, getToken, login } = useAuth()
  const [profile, setProfile] = useState<Profile | null>(null)
  const { cells, loading, done, error, loadMore } = useHomeTimeline(
    ready && authenticated
  )
  const sentinel = useInfiniteScroll(loadMore)

  useEffect(() => {
    if (!ready || !authenticated) return
    apiFetch("/users/me", getToken())
      .then((r) => (r.ok ? r.json() : null))
      .then(setProfile)
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, authenticated])

  if (ready && !authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <h1 className="font-serif text-3xl font-semibold italic">TinyInsta</h1>
        <p className="text-sm text-muted-foreground">Log in to see the feed.</p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-[975px] justify-center gap-8 px-4 py-6">
      <section className="w-full max-w-[630px]">
        <StoriesRow profile={profile} />

        <div className="space-y-2">
          {cells.map(({ post, imageUrl, author }) => (
            <PostCard
              key={post.post_id}
              post={post}
              imageUrl={imageUrl}
              authorName={author?.username ?? "unknown"}
              authorAvatar={author?.avatar_url}
            />
          ))}

          {loading && <FeedSkeleton />}

          {cells.length === 0 && done && !error && (
            <div className="space-y-3 py-12 text-center">
              <p className="text-sm text-muted-foreground">
                Your feed is empty. Follow people to see their posts here.
              </p>
              <Button asChild size="sm">
                <Link href="/upload">Share your first post</Link>
              </Button>
            </div>
          )}
          {error && (
            <p className="py-4 text-center text-sm text-destructive">{error}</p>
          )}
          <div ref={sentinel} className="h-px" />
        </div>
      </section>

      <aside className="hidden w-[320px] shrink-0 lg:block">
        <RightRail profile={profile} />
      </aside>
    </div>
  )
}

function FeedSkeleton() {
  return (
    <div className="border-b pb-3">
      <div className="flex items-center gap-3 py-3">
        <Skeleton className="size-8 rounded-full" />
        <Skeleton className="h-3.5 w-24" />
      </div>
      <Skeleton className="aspect-square w-full rounded-sm" />
      <div className="space-y-2 pt-3">
        <Skeleton className="h-3.5 w-16" />
        <Skeleton className="h-3.5 w-3/4" />
      </div>
    </div>
  )
}
