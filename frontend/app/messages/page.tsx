"use client"

import { Suspense, useCallback, useEffect, useRef, useState } from "react"
import { useSearchParams } from "next/navigation"

import {
  apiFetch,
  type Conversation,
  type Message,
  type MessagePage,
  type Profile,
} from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { useIncomingMessages } from "@/lib/use-realtime"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export default function MessagesPage() {
  return (
    <Suspense fallback={null}>
      <MessagesInner />
    </Suspense>
  )
}

function MessagesInner() {
  const { ready, authenticated, getToken, userId, login } = useAuth()
  const params = useSearchParams()
  const startWith = params.get("to")

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState("")
  const [profiles, setProfiles] = useState<Map<string, Profile>>(new Map())
  const bottom = useRef<HTMLDivElement | null>(null)

  const resolveProfile = useCallback(
    async (id: string) => {
      if (!id || profiles.has(id)) return
      const r = await apiFetch(`/users/${id}`, getToken())
      if (r.ok) {
        const p = (await r.json()) as Profile
        setProfiles((prev) => new Map(prev).set(p.user_id, p))
      }
    },
    [getToken, profiles]
  )

  // Load the inbox.
  useEffect(() => {
    if (!ready || !authenticated) return
    apiFetch("/messaging/conversations", getToken())
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((data: { items: Conversation[] }) => {
        setConversations(data.items)
        data.items.forEach((c) => resolveProfile(c.peer_id))
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, authenticated])

  // Open (or create) a conversation passed as ?to=<userId>.
  useEffect(() => {
    if (!ready || !authenticated || !startWith) return
    apiFetch("/messaging/conversations/start", getToken(), {
      method: "POST",
      body: JSON.stringify({ peer_id: startWith }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data: { conversation_id: string } | null) => {
        if (!data) return
        setSelected(data.conversation_id)
        resolveProfile(startWith)
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, authenticated, startWith])

  // Load the selected thread (newest-first from the API → reverse for display).
  useEffect(() => {
    if (!selected) return
    apiFetch(`/messaging/conversations/${selected}/messages`, getToken())
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((data: MessagePage) => setMessages([...data.items].reverse()))
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Live incoming messages: append to the open thread, refresh the inbox order.
  useIncomingMessages((m) => {
    if (m.conversation_id === selected) {
      setMessages((prev) =>
        prev.some((x) => x.message_id === m.message_id)
          ? prev
          : [
              ...prev,
              {
                message_id: m.message_id,
                sender_id: m.sender_id,
                recipient_id: userId ?? "",
                body: m.body,
                created_at: m.created_at,
              },
            ]
      )
    }
    setConversations((prev) =>
      prev.map((c) =>
        c.conversation_id === m.conversation_id
          ? { ...c, last_message: m.body, last_message_at: m.created_at }
          : c
      )
    )
  })

  const send = async () => {
    const body = draft.trim()
    if (!body || !selected) return
    setDraft("")
    const res = await apiFetch(
      `/messaging/conversations/${selected}/messages`,
      getToken(),
      { method: "POST", body: JSON.stringify({ body }) }
    )
    if (res.ok) {
      const msg = (await res.json()) as Message
      setMessages((prev) => [...prev, msg])
      setConversations((prev) =>
        prev.map((c) =>
          c.conversation_id === selected
            ? { ...c, last_message: body, last_message_at: msg.created_at }
            : c
        )
      )
    }
  }

  if (ready && !authenticated) {
    return (
      <div className="mx-auto max-w-sm space-y-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">
          Log in to see your messages.
        </p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  const peerOf = (c: Conversation) =>
    profiles.get(c.peer_id)?.username ?? c.peer_id.slice(0, 8)

  return (
    <div className="mx-auto flex h-[calc(100dvh-3rem)] w-full max-w-[935px] md:h-dvh">
      {/* Conversation list */}
      <aside
        className={cn(
          "w-full shrink-0 border-r md:w-[320px]",
          selected && "hidden md:block"
        )}
      >
        <h1 className="border-b px-4 py-4 text-lg font-semibold">Messages</h1>
        <ul className="divide-y">
          {conversations.map((c) => {
            const p = profiles.get(c.peer_id)
            const name = peerOf(c)
            return (
              <li key={c.conversation_id}>
                <button
                  type="button"
                  onClick={() => setSelected(c.conversation_id)}
                  className={cn(
                    "flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent",
                    selected === c.conversation_id && "bg-accent"
                  )}
                >
                  <Avatar className="size-11">
                    {p?.avatar_url && (
                      <AvatarImage src={p.avatar_url} alt={name} />
                    )}
                    <AvatarFallback>
                      {name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold">{name}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {c.last_message}
                    </span>
                  </span>
                </button>
              </li>
            )
          })}
          {conversations.length === 0 && (
            <li className="px-4 py-12 text-center text-sm text-muted-foreground">
              No conversations yet.
            </li>
          )}
        </ul>
      </aside>

      {/* Thread */}
      <section
        className={cn("flex flex-1 flex-col", !selected && "hidden md:flex")}
      >
        {selected ? (
          <>
            <header className="flex items-center gap-2 border-b px-4 py-3">
              <Button
                variant="ghost"
                size="sm"
                className="md:hidden"
                onClick={() => setSelected(null)}
              >
                Back
              </Button>
              <span className="text-sm font-semibold">
                {(() => {
                  const c = conversations.find(
                    (x) => x.conversation_id === selected
                  )
                  return c ? peerOf(c) : "Conversation"
                })()}
              </span>
            </header>
            <div className="flex-1 space-y-2 overflow-y-auto p-4">
              {messages.map((m) => (
                <div
                  key={m.message_id}
                  className={cn(
                    "flex",
                    m.sender_id === userId ? "justify-end" : "justify-start"
                  )}
                >
                  <span
                    className={cn(
                      "max-w-[75%] rounded-2xl px-3 py-2 text-sm",
                      m.sender_id === userId
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    )}
                  >
                    {m.body}
                  </span>
                </div>
              ))}
              <div ref={bottom} />
            </div>
            <form
              className="flex items-center gap-2 border-t p-3"
              onSubmit={(e) => {
                e.preventDefault()
                send()
              }}
            >
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Message…"
                className="flex-1"
              />
              <Button type="submit" disabled={!draft.trim()}>
                Send
              </Button>
            </form>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
            Select a conversation to start chatting.
          </div>
        )}
      </section>
    </div>
  )
}
