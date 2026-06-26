"use client"

import { useCallback, useEffect, useState } from "react"
import { IconPlus } from "@tabler/icons-react"

import { apiFetch, type Profile, type StoryGroup } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { StoryCameraDialog } from "@/components/story-camera-dialog"
import { StoryViewer } from "@/components/story-viewer"

// A single author's bubble in the bar. A coloured ring means "unseen": the
// usual gradient for public stories, green when the group is close-friends.
function ringClass(hasUnseen: boolean, closeFriends: boolean): string {
  if (!hasUnseen) return "rounded-full bg-muted p-[2px]"
  if (closeFriends) return "rounded-full bg-green-600 p-[2px]"
  return "rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[2px]"
}

function StoryBubble({
  profile,
  hasUnseen,
  closeFriends,
  onClick,
}: {
  profile: Profile
  hasUnseen: boolean
  closeFriends: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-16 shrink-0 flex-col items-center gap-1"
    >
      <div className={ringClass(hasUnseen, closeFriends)}>
        <div className="rounded-full bg-background p-[2px]">
          <Avatar className="size-14">
            {profile.avatar_url && (
              <AvatarImage src={profile.avatar_url} alt={profile.username} />
            )}
            <AvatarFallback>
              {profile.username.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
        </div>
      </div>
      <span className="w-full truncate text-center text-xs">
        {profile.username}
      </span>
    </button>
  )
}

const isCloseFriendsGroup = (g: StoryGroup) =>
  g.stories.some((s) => s.audience === "close_friends")

export function StoriesRow({ profile }: { profile: Profile | null }) {
  const { ready, authenticated, getToken } = useAuth()
  const [groups, setGroups] = useState<StoryGroup[]>([])
  const [profiles, setProfiles] = useState<Record<string, Profile>>({})
  const [loading, setLoading] = useState(true)
  const [viewerStart, setViewerStart] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (!ready || !authenticated) return
    try {
      const token = getToken()
      const res = await apiFetch("/stories/feed", token)
      if (!res.ok) throw new Error(`feed ${res.status}`)
      const { items }: { items: StoryGroup[] } = await res.json()

      // Resolve the author profile of each group (skip ones we already have).
      const entries = await Promise.all(
        items.map(async (g) => {
          const r = await apiFetch(`/users/${g.author_id}`, token)
          return r.ok
            ? ([g.author_id, (await r.json()) as Profile] as const)
            : null
        })
      )
      setProfiles((prev) => {
        const next = { ...prev }
        for (const e of entries) if (e) next[e[0]] = e[1]
        return next
      })
      setGroups(items)
    } catch {
      setGroups([])
    } finally {
      setLoading(false)
    }
  }, [ready, authenticated, getToken])

  useEffect(() => {
    // load() is memoized; it sets the loading state to kick off the fetch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
  }, [load])

  // Optimistically mark a group seen once its stories have been viewed, so the
  // ring greys out without a round-trip.
  function markGroupSeen(groupIdx: number) {
    setGroups((prev) =>
      prev.map((g, i) => (i === groupIdx ? { ...g, has_unseen: false } : g))
    )
  }

  const selfIdx = profile
    ? groups.findIndex((g) => g.author_id === profile.user_id)
    : -1
  const otherGroups = groups
    .map((g, i) => ({ g, i }))
    .filter(({ i }) => i !== selfIdx)

  return (
    <>
      <ScrollArea className="w-full">
        <div className="flex gap-4 pb-4">
          {/* "Your story" — always present: opens the camera, or your own
              story if you have one live. */}
          {profile ? (
            <div className="flex w-16 shrink-0 flex-col items-center gap-1">
              <div className="relative">
                {selfIdx >= 0 ? (
                  <StoryBubble
                    profile={profile}
                    hasUnseen={groups[selfIdx].has_unseen}
                    closeFriends={isCloseFriendsGroup(groups[selfIdx])}
                    onClick={() => setViewerStart(selfIdx)}
                  />
                ) : (
                  <div className="flex w-16 flex-col items-center gap-1">
                    <Avatar className="size-14">
                      {profile.avatar_url && (
                        <AvatarImage
                          src={profile.avatar_url}
                          alt={profile.username}
                        />
                      )}
                      <AvatarFallback>
                        {profile.username.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                  </div>
                )}
                <StoryCameraDialog
                  onPosted={load}
                  trigger={
                    <button
                      type="button"
                      aria-label="Add to your story"
                      className="absolute right-0 bottom-4 rounded-full border-2 border-background bg-primary p-0.5 text-primary-foreground"
                    >
                      <IconPlus className="size-3.5" />
                    </button>
                  }
                />
              </div>
              {selfIdx < 0 && (
                <span className="w-full truncate text-center text-xs">
                  Your story
                </span>
              )}
            </div>
          ) : (
            <div className="flex w-16 shrink-0 flex-col items-center gap-1">
              <Skeleton className="size-14 rounded-full" />
              <Skeleton className="h-3 w-12" />
            </div>
          )}

          {loading
            ? Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="flex w-16 shrink-0 flex-col items-center gap-1"
                >
                  <Skeleton className="size-14 rounded-full" />
                  <Skeleton className="h-3 w-12" />
                </div>
              ))
            : otherGroups.map(({ g, i }) => {
                const p = profiles[g.author_id]
                if (!p) return null
                return (
                  <StoryBubble
                    key={g.author_id}
                    profile={p}
                    hasUnseen={g.has_unseen}
                    closeFriends={isCloseFriendsGroup(g)}
                    onClick={() => setViewerStart(i)}
                  />
                )
              })}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>

      {viewerStart !== null && (
        <StoryViewer
          groups={groups}
          profiles={profiles}
          startIndex={viewerStart}
          onViewed={(gi) => markGroupSeen(gi)}
          onClose={() => setViewerStart(null)}
        />
      )}
    </>
  )
}
