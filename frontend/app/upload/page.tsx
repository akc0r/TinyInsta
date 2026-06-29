"use client"

import { useRouter } from "next/navigation"
import { useState, type FormEvent } from "react"

import { apiFetch, putToStorage, type Post, type UploadTicket } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { IconCheck } from "@tabler/icons-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"

export default function UploadPage() {
  const router = useRouter()
  const { ready, authenticated, getToken, login } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [caption, setCaption] = useState("")
  const [status, setStatus] = useState("")
  const [busy, setBusy] = useState(false)

  if (!ready) {
    return (
      <div className="mx-auto max-w-md space-y-4 p-6">
        <Skeleton className="h-6 w-28" />
        <div className="space-y-1.5">
          <Skeleton className="h-4 w-14" />
          <Skeleton className="h-8 w-full" />
        </div>
        <div className="space-y-1.5">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-16 w-full" />
        </div>
        <Skeleton className="h-9 w-16" />
      </div>
    )
  }

  if (!authenticated) {
    return (
      <div className="space-y-3 p-6">
        <p>You must be logged in to upload.</p>
        <Button onClick={login}>Log in</Button>
      </div>
    )
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    // A video upload becomes a reel (kind=reel); the media-worker transcodes it.
    const isVideo = file.type.startsWith("video")
    const mediaKind = isVideo ? "video" : "image"
    try {
      // 1) Ask media-svc for a presigned PUT URL.
      setStatus("Requesting upload URL…")
      const ticketRes = await apiFetch("/media/upload-url", getToken(), {
        method: "POST",
        body: JSON.stringify({ kind: mediaKind }),
      })
      if (!ticketRes.ok) throw new Error(`upload-url ${ticketRes.status}`)
      const ticket: UploadTicket = await ticketRes.json()

      // 2) PUT the bytes straight to storage (no Bearer token).
      setStatus("Uploading file…")
      const putRes = await putToStorage(ticket.upload_url, file)
      if (!putRes.ok) throw new Error(`storage PUT ${putRes.status}`)

      // 3) Mark the media as ready.
      setStatus("Registering media…")
      const mediaRes = await apiFetch("/media", getToken(), {
        method: "POST",
        body: JSON.stringify({ media_id: ticket.media_id, kind: mediaKind }),
      })
      if (!mediaRes.ok) throw new Error(`media ${mediaRes.status}`)

      // 4) Create the post (a video becomes a reel).
      setStatus("Creating post…")
      const postRes = await apiFetch("/posts", getToken(), {
        method: "POST",
        body: JSON.stringify({
          caption,
          media_ids: [ticket.media_id],
          kind: isVideo ? "reel" : "post",
        }),
      })
      if (!postRes.ok) throw new Error(`posts ${postRes.status}`)
      const post: Post = await postRes.json()

      setStatus("Done")
      router.push(`/profile?new=${post.post_id}`)
    } catch (err) {
      setStatus(`Error: ${(err as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4 p-6">
      <h1 className="text-lg font-semibold">New post</h1>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="photo">Photo or video</Label>
          <Input
            id="photo"
            type="file"
            accept="image/*,video/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file?.type.startsWith("video") && (
            <p className="text-xs text-muted-foreground">
              Videos are posted as Reels.
            </p>
          )}
        </div>
        {file &&
          (file.type.startsWith("video") ? (
            <video
              src={URL.createObjectURL(file)}
              className="aspect-square w-full rounded object-cover"
              controls
              muted
              playsInline
            />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={URL.createObjectURL(file)}
              alt="preview"
              className="aspect-square w-full rounded object-cover"
            />
          ))}
        <div className="space-y-1.5">
          <Label htmlFor="caption">Caption</Label>
          <Textarea
            id="caption"
            rows={3}
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Say something… #hello"
          />
        </div>
        <Button type="submit" disabled={!file || busy}>
          {busy ? "Posting…" : "Post"}
        </Button>
        {status && (
          <p className="flex items-center gap-1 text-sm text-muted-foreground">
            {status === "Done" && (
              <IconCheck className="size-4 text-green-600" />
            )}
            {status}
          </p>
        )}
      </form>
    </div>
  )
}
