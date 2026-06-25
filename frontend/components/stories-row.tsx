"use client"

import Link from "next/link"

import type { Profile } from "@/lib/api"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

function StoryAvatar({ profile }: { profile: Profile }) {
  return (
    <Link
      href={`/profile/${profile.user_id}`}
      className="flex w-16 shrink-0 flex-col items-center gap-1"
    >
      <div className="rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[2px]">
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
      <span className="w-full truncate text-center text-xs">{profile.username}</span>
    </Link>
  )
}

export function StoriesRow({ profile }: { profile: Profile | null }) {
  return (
    <ScrollArea className="w-full">
      <div className="flex gap-4 pb-4">
        {profile ? (
          <StoryAvatar profile={profile} />
        ) : (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex w-16 shrink-0 flex-col items-center gap-1">
              <Skeleton className="size-14 rounded-full" />
              <Skeleton className="h-3 w-12" />
            </div>
          ))
        )}
      </div>
      <ScrollBar orientation="horizontal" />
    </ScrollArea>
  )
}
