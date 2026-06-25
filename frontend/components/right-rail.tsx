"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { apiFetch, type Profile, type Suggestion } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

const FOOTER_LINKS = [
  "About",
  "Help",
  "Press",
  "API",
  "Jobs",
  "Privacy",
  "Terms",
  "Locations",
]

export function RightRail({ profile }: { profile: Profile | null }) {
  const { ready, authenticated, getToken, logout } = useAuth()
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null)

  useEffect(() => {
    if (!ready || !authenticated) return
    apiFetch("/users/me/suggestions", getToken())
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d: { items: Suggestion[] }) => setSuggestions(d.items))
      .catch(() => setSuggestions([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, authenticated])

  return (
    <div className="space-y-4 pt-2 text-sm">
      <div className="flex items-center gap-3">
        {profile ? (
          <>
            <Link
              href={`/profile/${profile.user_id}`}
              className="flex min-w-0 flex-1 items-center gap-3"
            >
              <Avatar className="size-11">
                {profile.avatar_url && (
                  <AvatarImage src={profile.avatar_url} alt={profile.username} />
                )}
                <AvatarFallback>
                  {profile.username.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold hover:underline">{profile.username}</p>
                <p className="truncate text-muted-foreground">
                  {profile.name || profile.bio || "Welcome to TinyInsta"}
                </p>
              </div>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              className="font-semibold text-primary"
            >
              Switch
            </Button>
          </>
        ) : (
          <>
            <Skeleton className="size-11 rounded-full" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="h-3 w-32" />
            </div>
          </>
        )}
      </div>

      <div className="flex items-center justify-between">
        <span className="font-semibold text-muted-foreground">Suggested for you</span>
        <button className="text-xs font-semibold">See All</button>
      </div>
      {suggestions === null ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="size-9 rounded-full" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-2.5 w-28" />
              </div>
            </div>
          ))}
        </div>
      ) : suggestions.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No suggestions yet — follow people to see them here.
        </p>
      ) : (
        <ul className="space-y-3">
          {suggestions.map((s) => (
            <SuggestionRow key={s.user_id} suggestion={s} />
          ))}
        </ul>
      )}

      <nav className="flex flex-wrap gap-x-2 gap-y-1 pt-4 text-xs text-muted-foreground/70">
        {FOOTER_LINKS.map((link) => (
          <span key={link} className="after:content-['·'] after:ml-2 last:after:content-['']">
            {link}
          </span>
        ))}
      </nav>
      <p className="text-xs text-muted-foreground/70">© 2026 TINYINSTA</p>
    </div>
  )
}

function SuggestionRow({ suggestion }: { suggestion: Suggestion }) {
  const { getToken } = useAuth()
  const [followed, setFollowed] = useState(false)
  const [pending, setPending] = useState(false)

  async function follow() {
    if (pending || followed) return
    setPending(true)
    setFollowed(true)
    try {
      const r = await apiFetch(`/users/${suggestion.user_id}/follow`, getToken(), {
        method: "POST",
      })
      if (!r.ok) throw new Error()
    } catch {
      setFollowed(false)
    } finally {
      setPending(false)
    }
  }

  const subtitle =
    suggestion.mutual > 0
      ? `Followed by ${suggestion.mutual} ${suggestion.mutual === 1 ? "person" : "people"} you follow`
      : suggestion.name || "Suggested for you"

  return (
    <li className="flex items-center gap-3">
      <Link
        href={`/profile/${suggestion.user_id}`}
        className="flex min-w-0 flex-1 items-center gap-3"
      >
        <Avatar className="size-9">
          {suggestion.avatar_url && (
            <AvatarImage src={suggestion.avatar_url} alt={suggestion.username} />
          )}
          <AvatarFallback>
            {suggestion.username.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold hover:underline">
            {suggestion.username}
          </p>
          <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </Link>
      <button
        onClick={follow}
        disabled={pending || followed}
        className="text-xs font-semibold text-primary disabled:text-muted-foreground"
      >
        {followed ? "Following" : "Follow"}
      </button>
    </li>
  )
}
