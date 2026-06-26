"use client"

import { use } from "react"
import { IconHash } from "@tabler/icons-react"

import { useAuth } from "@/lib/auth-context"
import { usePostHits } from "@/lib/use-search"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { PostGrid } from "@/components/post-grid"

export default function HashtagPage({
  params,
}: {
  params: Promise<{ tag: string }>
}) {
  const { tag } = use(params)
  const clean = decodeURIComponent(tag).replace(/^#/, "").toLowerCase()
  const { ready, authenticated, login } = useAuth()
  const { cells, loading, error } = usePostHits(
    `/hashtags/${encodeURIComponent(clean)}`,
    ready && authenticated
  )

  if (ready && !authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">Log in to see hashtags.</p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[935px] px-1 py-4 sm:px-4 sm:py-6">
      <header className="mb-6 flex items-center gap-3 px-3 sm:px-0">
        <span className="flex size-16 items-center justify-center rounded-full bg-muted">
          <IconHash className="size-7" />
        </span>
        <h1 className="text-xl font-semibold">#{clean}</h1>
      </header>

      {loading ? (
        <div className="grid grid-cols-3 gap-1">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square rounded-none" />
          ))}
        </div>
      ) : error ? (
        <p className="py-12 text-center text-sm text-destructive">{error}</p>
      ) : cells.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No posts tagged #{clean} yet.
        </p>
      ) : (
        <PostGrid cells={cells} />
      )}
    </div>
  )
}
