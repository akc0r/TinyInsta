"use client"

import { useEffect, useState } from "react"

import { apiFetch, type SavedItem } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { hydratePostIds, type HydratedPost } from "@/lib/use-timeline"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { PostGrid } from "@/components/post-grid"

export default function SavedPage() {
  const { ready, authenticated, getToken, login } = useAuth()
  const [cells, setCells] = useState<HydratedPost[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ready || !authenticated) return
    const token = getToken()
    apiFetch("/posts/saves", token)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then(async (data: { items: SavedItem[] }) => {
        const ids = data.items.map((s) => s.post_id)
        setCells(await hydratePostIds(ids, token))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, authenticated])

  if (ready && !authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">
          Log in to see saved posts.
        </p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[935px] px-4 py-6">
      <h1 className="mb-4 text-xl font-semibold">Saved</h1>
      {loading ? (
        <div className="grid grid-cols-3 gap-1">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square" />
          ))}
        </div>
      ) : cells.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          You haven&apos;t saved any posts yet.
        </p>
      ) : (
        <PostGrid cells={cells} />
      )}
    </div>
  )
}
