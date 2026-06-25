"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { IconStar, IconX } from "@tabler/icons-react"

import { apiFetch, type Media, type Profile, type StoryGroup } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

const STORY_DURATION_MS = 5000

// Resolve a media id to its image URL, memoised across the viewer's lifetime.
function useMediaUrls() {
  const { getToken } = useAuth()
  const cache = useRef<Map<string, string>>(new Map())
  return useCallback(
    async (mediaId: string): Promise<string | null> => {
      const hit = cache.current.get(mediaId)
      if (hit) return hit
      const res = await apiFetch(`/media/${mediaId}`, getToken())
      if (!res.ok) return null
      const url = ((await res.json()) as Media).original_url
      cache.current.set(mediaId, url)
      return url
    },
    [getToken],
  )
}

export function StoryViewer({
  groups,
  profiles,
  startIndex,
  onClose,
  onViewed,
}: {
  groups: StoryGroup[]
  profiles: Record<string, Profile>
  startIndex: number
  onClose: () => void
  onViewed?: (group: number, story: number) => void
}) {
  const { getToken } = useAuth()
  const resolveMedia = useMediaUrls()
  const [groupIdx, setGroupIdx] = useState(startIndex)
  const [storyIdx, setStoryIdx] = useState(0)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  const group = groups[groupIdx]
  const story = group?.stories[storyIdx]
  const author = group ? profiles[group.author_id] : undefined

  const next = useCallback(() => {
    setStoryIdx((si) => {
      const g = groups[groupIdx]
      if (g && si + 1 < g.stories.length) return si + 1
      setGroupIdx((gi) => {
        if (gi + 1 < groups.length) return gi + 1
        onClose()
        return gi
      })
      return 0
    })
  }, [groupIdx, groups, onClose])

  const prev = useCallback(() => {
    setStoryIdx((si) => {
      if (si > 0) return si - 1
      setGroupIdx((gi) => Math.max(0, gi - 1))
      // Jump to the last story of the previous group.
      const target = groups[Math.max(0, groupIdx - 1)]
      return groupIdx > 0 ? target.stories.length - 1 : 0
    })
  }, [groupIdx, groups])

  // Resolve the current story's image whenever it changes.
  useEffect(() => {
    if (!story) return
    let active = true
    setImageUrl(null)
    resolveMedia(story.media_id).then((url) => {
      if (active) setImageUrl(url)
    })
    return () => {
      active = false
    }
  }, [story, resolveMedia])

  // Record the view (idempotent server-side) and bubble it up so the bar can
  // recompute its unseen rings on close.
  useEffect(() => {
    if (!story) return
    apiFetch(`/stories/${story.story_id}/view`, getToken(), { method: "POST" }).catch(
      () => {},
    )
    onViewed?.(groupIdx, storyIdx)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [story?.story_id])

  // Auto-advance timer with a progress bar, reset on each story.
  useEffect(() => {
    if (!story || !imageUrl) return
    setProgress(0)
    const start = Date.now()
    const id = setInterval(() => {
      const elapsed = Date.now() - start
      const ratio = Math.min(1, elapsed / STORY_DURATION_MS)
      setProgress(ratio)
      if (ratio >= 1) {
        clearInterval(id)
        next()
      }
    }, 50)
    return () => clearInterval(id)
  }, [story?.story_id, imageUrl, next])

  // Keyboard navigation.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose()
      else if (e.key === "ArrowRight") next()
      else if (e.key === "ArrowLeft") prev()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [next, prev, onClose])

  if (!group || !story) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
      <div className="relative flex aspect-[9/16] h-full max-h-[92vh] w-full max-w-md flex-col overflow-hidden rounded-lg bg-black">
        {/* Segmented progress bar, one segment per story in the group. */}
        <div className="absolute inset-x-0 top-0 z-20 flex gap-1 p-2">
          {group.stories.map((s, i) => (
            <div key={s.story_id} className="h-0.5 flex-1 overflow-hidden rounded bg-white/30">
              <div
                className="h-full bg-white"
                style={{
                  width: `${i < storyIdx ? 100 : i === storyIdx ? progress * 100 : 0}%`,
                }}
              />
            </div>
          ))}
        </div>

        <div className="absolute inset-x-0 top-0 z-20 flex items-center gap-2 p-3 pt-5">
          <Avatar className="size-8 ring-2 ring-white/80">
            {author?.avatar_url && (
              <AvatarImage src={author.avatar_url} alt={author.username} />
            )}
            <AvatarFallback>
              {(author?.username ?? "?").charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <span className="text-sm font-semibold text-white drop-shadow">
            {author?.username ?? "unknown"}
          </span>
          {story.audience === "close_friends" && (
            <span className="flex items-center gap-1 rounded-full bg-green-600 px-2 py-0.5 text-xs font-medium text-white">
              <IconStar className="size-3 fill-white" /> Close friends
            </span>
          )}
          <button
            type="button"
            onClick={onClose}
            className="ml-auto rounded-full p-1 text-white"
            aria-label="Close"
          >
            <IconX className="size-6" />
          </button>
        </div>

        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={imageUrl} alt="story" className="size-full object-contain" />
        ) : (
          <div className="flex size-full items-center justify-center text-white/60">
            Loading…
          </div>
        )}

        {/* Tap zones: left third = previous, right two-thirds = next. */}
        <button
          type="button"
          aria-label="Previous"
          onClick={prev}
          className="absolute inset-y-0 left-0 z-10 w-1/3"
        />
        <button
          type="button"
          aria-label="Next"
          onClick={next}
          className="absolute inset-y-0 right-0 z-10 w-2/3"
        />
      </div>
    </div>
  )
}
