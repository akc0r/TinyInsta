"use client"

import { useEffect, useRef, useState } from "react"

import { apiFetch, type Notification } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { realtime, type RealtimeMessage } from "@/lib/realtime"

type PostHandlers = {
  onLiked?: (count: number) => void
  onCommented?: (msg: { post_id: string; comment_id: string }) => void
}

// Subscribe a post card to its live like/comment counters. Handlers are kept in
// a ref so the subscription itself only depends on the post id.
export function usePostRealtime(postId: string, handlers: PostHandlers) {
  const { getToken } = useAuth()
  const ref = useRef(handlers)
  useEffect(() => {
    ref.current = handlers
  })

  useEffect(() => {
    realtime.configure(getToken)
    const off = realtime.subscribePost(postId, (msg: RealtimeMessage) => {
      if (msg.type === "post.liked") ref.current.onLiked?.(msg.count)
      else if (msg.type === "post.commented") ref.current.onCommented?.(msg)
    })
    return off
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId])
}

// The viewer's notification feed: initial fetch over REST, then live updates
// pushed over the WebSocket. Used by the notifications page and the nav badge.
export function useNotifications(enabled: boolean) {
  const { getToken } = useAuth()
  const [items, setItems] = useState<Notification[]>([])
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    if (!enabled) return
    apiFetch("/notifications", getToken())
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return
        setItems(data.items)
        setUnread(data.unread)
      })
      .catch(() => {})

    realtime.configure(getToken)
    const off = realtime.onNotification((msg) => {
      if (msg.type !== "notification") return
      const note: Notification = {
        id: msg.id,
        notification_type: msg.notification_type as Notification["notification_type"],
        payload: msg.payload,
        read: msg.read,
        created_at: msg.created_at,
      }
      setItems((prev) => [note, ...prev])
      setUnread((n) => n + 1)
    })
    return off
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])

  const markRead = (id: string) => {
    apiFetch(`/notifications/${id}/read`, getToken(), { method: "POST" }).catch(
      () => {},
    )
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)))
    setUnread((n) => Math.max(0, n - 1))
  }

  return { items, unread, markRead }
}
