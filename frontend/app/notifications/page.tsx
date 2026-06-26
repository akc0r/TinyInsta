"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { apiFetch, type Notification, type Profile } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { useNotifications } from "@/lib/use-realtime"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"

function summary(n: Notification, actor: string): string {
  switch (n.notification_type) {
    case "follow":
      return `${actor} started following you.`
    case "comment":
      return `${actor} commented: ${n.payload.body ?? ""}`.trim()
    case "like":
      return `${actor} liked your post.`
    default:
      return "New activity."
  }
}

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

export default function NotificationsPage() {
  const { ready, authenticated, getToken, login } = useAuth()
  const { items, markRead } = useNotifications(ready && authenticated)
  const [names, setNames] = useState<Map<string, Profile>>(new Map())

  // Resolve actor ids to usernames/avatars (cached across renders).
  useEffect(() => {
    const ids = [
      ...new Set(items.map((n) => n.payload.actor_id).filter(Boolean)),
    ]
    const missing = ids.filter((id) => !names.has(id))
    if (missing.length === 0) return
    Promise.all(
      missing.map(async (id) => {
        const r = await apiFetch(`/users/${id}`, getToken())
        return r.ok ? ((await r.json()) as Profile) : null
      })
    ).then((profiles) => {
      setNames((prev) => {
        const next = new Map(prev)
        profiles.forEach((p) => p && next.set(p.user_id, p))
        return next
      })
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items])

  if (ready && !authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">
          Log in to see notifications.
        </p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[600px] px-4 py-6">
      <h1 className="mb-4 text-xl font-semibold">Notifications</h1>
      {items.length === 0 && (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No notifications yet.
        </p>
      )}
      <ul className="divide-y">
        {items.map((n) => {
          const actor = names.get(n.payload.actor_id)
          const actorName =
            actor?.username ?? n.payload.actor_id?.slice(0, 8) ?? "Someone"
          return (
            <li
              key={n.id}
              onClick={() => !n.read && markRead(n.id)}
              className={`flex cursor-pointer items-center gap-3 py-3 ${
                n.read ? "" : "bg-accent/40"
              }`}
            >
              <Link href={`/profile/${n.payload.actor_id}`}>
                <Avatar className="size-9">
                  {actor?.avatar_url && (
                    <AvatarImage src={actor.avatar_url} alt={actorName} />
                  )}
                  <AvatarFallback>
                    {actorName.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </Link>
              <p className="flex-1 text-sm">{summary(n, actorName)}</p>
              <span className="text-xs text-muted-foreground">
                {timeAgo(n.created_at)}
              </span>
              {!n.read && <span className="size-2 rounded-full bg-blue-500" />}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
