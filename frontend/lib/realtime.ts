import { WS_URL } from "@/lib/api"

// A single shared WebSocket to realtime-svc for the whole app. Components
// subscribe to the posts on screen (live like/comment counters) and to their
// own notification stream; the client multiplexes everything over one socket
// and transparently reconnects.

export type RealtimeMessage =
  | { type: "post.liked"; post_id: string; count: number }
  | { type: "post.commented"; post_id: string; comment_id: string }
  | { type: "notification"; id: string; notification_type: string; payload: Record<string, string>; read: boolean; created_at: string }

type Handler = (msg: RealtimeMessage) => void

class RealtimeClient {
  private ws: WebSocket | null = null
  private getToken: (() => string | undefined) | null = null
  private postHandlers = new Map<string, Set<Handler>>()
  private notifHandlers = new Set<Handler>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  // Wire the token source and open the socket (idempotent).
  configure(getToken: () => string | undefined) {
    this.getToken = getToken
    this.ensure()
  }

  private ensure() {
    if (typeof window === "undefined") return
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING)
    )
      return
    const token = this.getToken?.()
    if (!token) return

    const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`)
    this.ws = ws
    ws.onopen = () => {
      // (Re)subscribe to every post that currently has a listener.
      for (const postId of this.postHandlers.keys()) {
        this.send({ action: "subscribe", post_id: postId })
      }
    }
    ws.onmessage = (event) => this.dispatch(event.data)
    ws.onclose = () => {
      this.ws = null
      this.scheduleReconnect()
    }
    ws.onerror = () => ws.close()
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.ensure()
    }, 2000)
  }

  private send(payload: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload))
    }
  }

  private dispatch(raw: string) {
    let msg: RealtimeMessage
    try {
      msg = JSON.parse(raw)
    } catch {
      return
    }
    if (msg.type === "notification") {
      this.notifHandlers.forEach((h) => h(msg))
      return
    }
    if ("post_id" in msg) {
      this.postHandlers.get(msg.post_id)?.forEach((h) => h(msg))
    }
  }

  // Subscribe to a post's live counters. Returns an unsubscribe function.
  subscribePost(postId: string, handler: Handler): () => void {
    let set = this.postHandlers.get(postId)
    if (!set) {
      set = new Set()
      this.postHandlers.set(postId, set)
      this.send({ action: "subscribe", post_id: postId })
    }
    set.add(handler)
    this.ensure()

    return () => {
      const handlers = this.postHandlers.get(postId)
      if (!handlers) return
      handlers.delete(handler)
      if (handlers.size === 0) {
        this.postHandlers.delete(postId)
        this.send({ action: "unsubscribe", post_id: postId })
      }
    }
  }

  // Subscribe to the viewer's notification stream. Returns an unsubscribe fn.
  onNotification(handler: Handler): () => void {
    this.notifHandlers.add(handler)
    this.ensure()
    return () => this.notifHandlers.delete(handler)
  }
}

export const realtime = new RealtimeClient()
