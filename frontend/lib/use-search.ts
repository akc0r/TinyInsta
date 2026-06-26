"use client"

import { useEffect, useState } from "react"

import { apiFetch, type PostHit, type SearchResults } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { hydratePostIds, type HydratedPost } from "@/lib/use-timeline"

// Fetch a `{ items: PostHit[] }` endpoint (explore, hashtags) and hydrate the
// post ids into image cells. Re-runs whenever `path` changes; a flag drops a
// stale response if the path changed while a request was in flight.
export function usePostHits(path: string | null, enabled: boolean) {
  const { getToken } = useAuth()
  const [cells, setCells] = useState<HydratedPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!enabled || !path) return
    let cancelled = false
    setLoading(true)
    setError("")
    ;(async () => {
      try {
        const token = getToken()
        const res = await apiFetch(path, token)
        if (!res.ok) throw new Error(`${res.status}`)
        const { items }: { items: PostHit[] } = await res.json()
        const hydrated = await hydratePostIds(
          items.map((p) => p.post_id),
          token
        )
        if (!cancelled) setCells(hydrated)
      } catch (err) {
        if (!cancelled) setError((err as Error).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [path, enabled, getToken])

  return { cells, loading, error }
}

// Debounced combined search (users + posts) for the search bar. Empty query
// clears results without hitting the API.
export function useSearch(query: string, enabled: boolean) {
  const { getToken } = useAuth()
  const [results, setResults] = useState<SearchResults>({
    users: [],
    posts: [],
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const q = query.trim()
    if (!enabled || !q) {
      setResults({ users: [], posts: [] })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const res = await apiFetch(
          `/search?q=${encodeURIComponent(q)}`,
          getToken()
        )
        const data: SearchResults = res.ok
          ? await res.json()
          : { users: [], posts: [] }
        if (!cancelled) setResults(data)
      } catch {
        if (!cancelled) setResults({ users: [], posts: [] })
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query, enabled, getToken])

  return { results, loading }
}
