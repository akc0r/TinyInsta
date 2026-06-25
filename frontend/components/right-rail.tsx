"use client"

import Link from "next/link"

import type { Profile } from "@/lib/api"
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
  const { logout } = useAuth()

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
      <p className="text-xs text-muted-foreground">
        No suggestions yet — follow people to see them here.
      </p>

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
