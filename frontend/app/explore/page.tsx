"use client"

import { useAuth } from "@/lib/auth-context"
import { usePostHits } from "@/lib/use-search"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { PostGrid } from "@/components/post-grid"

export default function ExplorePage() {
  const { ready, authenticated, login } = useAuth()
  const { cells, loading, error } = usePostHits(
    "/explore",
    ready && authenticated
  )

  if (ready && !authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">Log in to explore.</p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[935px] px-1 py-1 sm:px-4 sm:py-6">
      {loading ? (
        <div className="grid grid-cols-3 gap-1">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square rounded-none" />
          ))}
        </div>
      ) : error ? (
        <p className="py-12 text-center text-sm text-destructive">{error}</p>
      ) : cells.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          Nothing to explore yet.
        </p>
      ) : (
        <PostGrid cells={cells} />
      )}
    </div>
  )
}
