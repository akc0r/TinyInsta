"use client"

import Link from "next/link"
import { useState } from "react"
import { IconHash, IconSearch } from "@tabler/icons-react"

import { useAuth } from "@/lib/auth-context"
import { useSearch } from "@/lib/use-search"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export default function SearchPage() {
  const { ready, authenticated, login } = useAuth()
  const [query, setQuery] = useState("")
  const { results, loading } = useSearch(query, ready && authenticated)

  const q = query.trim()
  const tag = q.replace(/^#/, "").toLowerCase()

  if (ready && !authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">Log in to search.</p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  const empty =
    !loading && q && results.users.length === 0 && results.posts.length === 0

  return (
    <div className="mx-auto w-full max-w-[600px] px-4 py-6">
      <div className="relative mb-6">
        <IconSearch className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search users and hashtags"
          className="pl-9"
        />
      </div>

      {!q && (
        <p className="py-12 text-center text-sm text-muted-foreground">
          Search for people, captions and #hashtags.
        </p>
      )}

      {q && (
        <div className="space-y-1">
          {/* Always offer a jump to the hashtag page for the typed term. */}
          {tag && (
            <Link
              href={`/hashtags/${encodeURIComponent(tag)}`}
              className="flex items-center gap-3 rounded-lg p-2 hover:bg-accent"
            >
              <span className="flex size-11 items-center justify-center rounded-full bg-muted">
                <IconHash className="size-5" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold">#{tag}</p>
                <p className="text-xs text-muted-foreground">
                  See tagged posts
                </p>
              </div>
            </Link>
          )}

          {results.users.length > 0 && (
            <p className="px-2 pt-3 pb-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Accounts
            </p>
          )}
          {results.users.map((u) => (
            <Link
              key={u.user_id}
              href={`/profile/${u.user_id}`}
              className="flex items-center gap-3 rounded-lg p-2 hover:bg-accent"
            >
              <Avatar className="size-11">
                <AvatarFallback>
                  {u.username.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{u.username}</p>
                {u.bio && (
                  <p className="truncate text-xs text-muted-foreground">
                    {u.bio}
                  </p>
                )}
              </div>
            </Link>
          ))}

          {results.posts.length > 0 && (
            <p className="px-2 pt-3 pb-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Posts
            </p>
          )}
          {results.posts.map((p) => (
            <Link
              key={p.post_id}
              href={`/profile/${p.author_id}`}
              className="flex items-center gap-3 rounded-lg p-2 hover:bg-accent"
            >
              <span className="flex size-11 items-center justify-center rounded-md bg-muted">
                <IconSearch className="size-4 text-muted-foreground" />
              </span>
              <p className="min-w-0 truncate text-sm">
                {p.caption ||
                  p.hashtags.map((h) => `#${h}`).join(" ") ||
                  "Post"}
              </p>
            </Link>
          ))}

          {empty && (
            <p className="py-12 text-center text-sm text-muted-foreground">
              No results for “{q}”.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
