"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import {
  IconBookmark,
  IconHeart,
  IconLayoutGrid,
  IconLink,
  IconMessageCircle,
  IconUserSquareRounded,
} from "@tabler/icons-react"

import { apiFetch, type Profile } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { useInfiniteScroll, useTimeline } from "@/lib/use-timeline"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { EditProfileDialog } from "@/components/edit-profile-dialog"
import { FollowListDialog } from "@/components/follow-list-dialog"

export function ProfileView({ userId: propUserId }: { userId?: string }) {
  const { ready, authenticated, userId: myId, getToken, login } = useAuth()
  const targetId = propUserId ?? myId
  const isMe = !!targetId && targetId === myId

  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const [following, setFollowing] = useState(false)
  const [followPending, setFollowPending] = useState(false)

  const {
    cells,
    loading: gridLoading,
    done,
    error,
    loadMore,
  } = useTimeline(targetId, 12)
  const sentinel = useInfiniteScroll(loadMore)

  useEffect(() => {
    if (!ready || !authenticated || !targetId) return
    setLoading(true)
    setNotFound(false)
    apiFetch(isMe ? "/users/me" : `/users/${targetId}`, getToken())
      .then((r) => {
        if (r.status === 404) {
          setNotFound(true)
          return null
        }
        return r.ok ? r.json() : null
      })
      .then((p: Profile | null) => {
        if (!p) return
        setProfile(p)
        setFollowing(!!p.is_following)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, authenticated, targetId])

  async function toggleFollow() {
    if (!profile || followPending) return
    const next = !following
    // Optimistic: flip the button and bump the visible follower count.
    setFollowPending(true)
    setFollowing(next)
    setProfile((p) =>
      p ? { ...p, followers: (p.followers ?? 0) + (next ? 1 : -1) } : p
    )
    try {
      const r = await apiFetch(`/users/${profile.user_id}/follow`, getToken(), {
        method: next ? "POST" : "DELETE",
      })
      if (!r.ok) throw new Error()
    } catch {
      // Roll back on failure.
      setFollowing(!next)
      setProfile((p) =>
        p ? { ...p, followers: (p.followers ?? 0) + (next ? -1 : 1) } : p
      )
    } finally {
      setFollowPending(false)
    }
  }

  if (!ready || (authenticated && loading)) return <ProfileSkeleton />

  if (!authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">
          You must be logged in to view profiles.
        </p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  if (notFound || !profile) {
    return (
      <div className="mx-auto max-w-sm space-y-2 px-4 py-16 text-center">
        <h1 className="text-lg font-semibold">User not found</h1>
        <p className="text-sm text-muted-foreground">
          This profile doesn’t exist.
        </p>
        <Button asChild variant="outline" size="sm">
          <Link href="/">Back home</Link>
        </Button>
      </div>
    )
  }

  const { username } = profile
  const postCount = done ? cells.length : `${cells.length}+`

  return (
    <div className="mx-auto max-w-[935px] px-4 py-8">
      <header className="flex flex-col items-center gap-6 px-2 sm:flex-row sm:items-start sm:gap-16">
        <Avatar className="size-20 sm:size-36">
          {profile.avatar_url && (
            <AvatarImage src={profile.avatar_url} alt={username} />
          )}
          <AvatarFallback className="text-3xl">
            {username.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 space-y-5">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl">{username}</h1>
            {isMe ? (
              <>
                <EditProfileDialog
                  profile={profile}
                  onSaved={setProfile}
                  trigger={
                    <Button variant="outline" size="sm">
                      Edit profile
                    </Button>
                  }
                />
                <Button asChild variant="outline" size="sm">
                  <Link href="/upload">New post</Link>
                </Button>
              </>
            ) : (
              <Button
                size="sm"
                variant={following ? "outline" : "default"}
                onClick={toggleFollow}
                disabled={followPending}
              >
                {following ? "Following" : "Follow"}
              </Button>
            )}
          </div>

          <div className="flex gap-8 text-sm">
            <span>
              <b>{postCount}</b> posts
            </span>
            <FollowListDialog
              userId={profile.user_id}
              kind="followers"
              trigger={
                <button className="hover:cursor-pointer hover:underline">
                  <b>{profile.followers ?? 0}</b> followers
                </button>
              }
            />
            <FollowListDialog
              userId={profile.user_id}
              kind="following"
              trigger={
                <button className="hover:cursor-pointer hover:underline">
                  <b>{profile.following ?? 0}</b> following
                </button>
              }
            />
          </div>

          <div className="space-y-0.5 text-sm">
            {profile.name && <p className="font-semibold">{profile.name}</p>}
            {profile.bio && (
              <p className="whitespace-pre-line">{profile.bio}</p>
            )}
            {profile.link && (
              <a
                href={profile.link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 font-semibold text-primary"
              >
                <IconLink className="size-4" />
                {profile.link.replace(/^https?:\/\//, "")}
              </a>
            )}
          </div>
        </div>
      </header>

      <Separator className="mt-8" />
      <div className="flex justify-center">
        <span className="-mt-px flex items-center gap-1.5 border-t border-foreground py-3 text-xs font-semibold tracking-wide text-foreground uppercase">
          <IconLayoutGrid className="size-3.5" /> Posts
        </span>
        <span className="flex items-center gap-1.5 px-8 py-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          <IconBookmark className="size-3.5" /> Saved
        </span>
        <span className="flex items-center gap-1.5 py-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          <IconUserSquareRounded className="size-3.5" /> Tagged
        </span>
      </div>

      <div className="mt-1 grid grid-cols-3 gap-1">
        {cells.map(({ post, imageUrl }) => (
          <div
            key={post.post_id}
            className="group relative aspect-square overflow-hidden bg-muted"
          >
            {imageUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={imageUrl}
                alt={post.caption}
                className="h-full w-full object-cover"
              />
            )}
            <div className="absolute inset-0 hidden items-center justify-center gap-6 bg-black/30 text-sm font-semibold text-white group-hover:flex">
              <span className="flex items-center gap-1.5">
                <IconHeart className="size-5 fill-white" /> 0
              </span>
              <span className="flex items-center gap-1.5">
                <IconMessageCircle className="size-5 fill-white" /> 0
              </span>
            </div>
          </div>
        ))}
      </div>

      {gridLoading && (
        <div className="mt-1 grid grid-cols-3 gap-1">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square rounded-none" />
          ))}
        </div>
      )}
      {cells.length === 0 && done && !error && (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No posts yet.
        </p>
      )}
      {error && (
        <p className="py-4 text-center text-sm text-destructive">{error}</p>
      )}
      <div ref={sentinel} className="h-px" />
    </div>
  )
}

function ProfileSkeleton() {
  return (
    <div className="mx-auto max-w-[935px] px-4 py-8">
      <div className="flex flex-col items-center gap-6 px-2 sm:flex-row sm:items-start sm:gap-16">
        <Skeleton className="size-20 rounded-full sm:size-36" />
        <div className="flex-1 space-y-5">
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-7 w-24" />
          </div>
          <div className="flex gap-8">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
          </div>
          <Skeleton className="h-4 w-48" />
        </div>
      </div>
      <Separator className="mt-8 mb-1" />
      <div className="grid grid-cols-3 gap-1 pt-3">
        {Array.from({ length: 9 }).map((_, i) => (
          <Skeleton key={i} className="aspect-square rounded-none" />
        ))}
      </div>
    </div>
  )
}
