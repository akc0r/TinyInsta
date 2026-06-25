"use client"

import Link from "next/link"
import { useState, type ReactNode } from "react"

import { apiFetch, type Profile } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

const LABELS = {
  followers: "Followers",
  following: "Following",
} as const

export function FollowListDialog({
  userId,
  kind,
  trigger,
}: {
  userId: string
  kind: "followers" | "following"
  trigger: ReactNode
}) {
  const { getToken } = useAuth()
  const [open, setOpen] = useState(false)
  const [users, setUsers] = useState<Profile[] | null>(null)

  // Fetch lazily each time the dialog opens so counts stay fresh.
  function onOpenChange(next: boolean) {
    setOpen(next)
    if (next) {
      setUsers(null)
      apiFetch(`/users/${userId}/${kind}`, getToken())
        .then((r) => (r.ok ? r.json() : { items: [] }))
        .then((d: { items: Profile[] }) => setUsers(d.items))
        .catch(() => setUsers([]))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="gap-0 p-0 sm:max-w-sm">
        <DialogHeader className="border-b px-4 py-3">
          <DialogTitle className="text-center text-base">{LABELS[kind]}</DialogTitle>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh]">
          <div className="p-2">
            {users === null ? (
              Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-2 py-2">
                  <Skeleton className="size-11 rounded-full" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-2.5 w-32" />
                  </div>
                </div>
              ))
            ) : users.length === 0 ? (
              <p className="px-2 py-10 text-center text-sm text-muted-foreground">
                {kind === "followers" ? "No followers yet." : "Not following anyone yet."}
              </p>
            ) : (
              users.map((u) => (
                <Link
                  key={u.user_id}
                  href={`/profile/${u.user_id}`}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-accent"
                >
                  <Avatar className="size-11">
                    {u.avatar_url && <AvatarImage src={u.avatar_url} alt={u.username} />}
                    <AvatarFallback>{u.username.charAt(0).toUpperCase()}</AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{u.username}</p>
                    {u.name && (
                      <p className="truncate text-sm text-muted-foreground">{u.name}</p>
                    )}
                  </div>
                </Link>
              ))
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
