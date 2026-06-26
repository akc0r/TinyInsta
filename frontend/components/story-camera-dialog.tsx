"use client"

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import {
  IconCamera,
  IconPhoto,
  IconRotateClockwise,
  IconStar,
  IconX,
} from "@tabler/icons-react"

import { apiFetch, uploadMedia } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

type Facing = "user" | "environment"

export function StoryCameraDialog({
  trigger,
  onPosted,
}: {
  trigger: ReactNode
  onPosted?: () => void
}) {
  const { getToken } = useAuth()
  const [open, setOpen] = useState(false)
  const [facing, setFacing] = useState<Facing>("user")
  const [captured, setCaptured] = useState<Blob | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [closeFriends, setCloseFriends] = useState(false)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  const startCamera = useCallback(
    async (mode: Facing) => {
      stopCamera()
      setError("")
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: mode },
          audio: false,
        })
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play().catch(() => {})
        }
      } catch {
        // No camera / permission denied → the file fallback still works.
        setError("Camera unavailable — pick a photo instead.")
      }
    },
    [stopCamera]
  )

  // Drive the camera from the dialog's open state and the capture state.
  useEffect(() => {
    // startCamera clears the error on (re)start — an intentional reset, not a render loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (open && !captured) startCamera(facing)
    else stopCamera()
    return stopCamera
  }, [open, captured, facing, startCamera, stopCamera])

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  function reset() {
    setCaptured(null)
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return null
    })
    setCloseFriends(false)
    setError("")
    setBusy(false)
  }

  function onOpenChange(next: boolean) {
    if (!next) reset()
    setOpen(next)
  }

  function applyCapture(blob: Blob) {
    setCaptured(blob)
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(blob)
    })
  }

  function capture() {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement("canvas")
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    // Mirror the front camera so the capture matches the live preview.
    if (facing === "user") {
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
    }
    ctx.drawImage(video, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (blob) applyCapture(blob)
      },
      "image/jpeg",
      0.9
    )
  }

  function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) applyCapture(f)
    e.target.value = ""
  }

  async function share() {
    if (!captured) return
    setBusy(true)
    setError("")
    try {
      const token = getToken()
      const file = new File([captured], "story.jpg", { type: "image/jpeg" })
      const mediaId = await uploadMedia(token, file, "image")
      const res = await apiFetch("/stories", token, {
        method: "POST",
        body: JSON.stringify({
          media_id: mediaId,
          audience: closeFriends ? "close_friends" : "public",
        }),
      })
      if (!res.ok) throw new Error(`stories ${res.status}`)
      onPosted?.()
      onOpenChange(false)
    } catch (err) {
      setError(`Error: ${(err as Error).message}`)
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add to your story</DialogTitle>
          <DialogDescription>
            Capture a photo from your camera. It disappears after 24 hours.
          </DialogDescription>
        </DialogHeader>

        <div className="relative aspect-[9/16] w-full overflow-hidden rounded-lg bg-black">
          {previewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={previewUrl}
              alt="story preview"
              className="size-full object-cover"
            />
          ) : (
            <video
              ref={videoRef}
              playsInline
              muted
              className={`size-full object-cover ${facing === "user" ? "-scale-x-100" : ""}`}
            />
          )}

          {!captured && (
            <button
              type="button"
              onClick={() =>
                setFacing((f) => (f === "user" ? "environment" : "user"))
              }
              className="absolute top-3 right-3 rounded-full bg-black/50 p-2 text-white"
              aria-label="Flip camera"
            >
              <IconRotateClockwise className="size-5" />
            </button>
          )}
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={onFilePicked}
        />

        {captured ? (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setCloseFriends((v) => !v)}
              disabled={busy}
              className={`flex w-full items-center justify-center gap-2 rounded-md border py-2 text-sm font-medium transition-colors ${
                closeFriends
                  ? "border-green-600 bg-green-600/10 text-green-600"
                  : "text-muted-foreground"
              }`}
            >
              <IconStar
                className={`size-4 ${closeFriends ? "fill-green-600" : ""}`}
              />
              {closeFriends ? "Close friends only" : "Share to everyone"}
            </button>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={reset}
                disabled={busy}
              >
                <IconX className="size-4" /> Retake
              </Button>
              <Button
                type="button"
                className="flex-1"
                onClick={share}
                disabled={busy}
              >
                {busy ? "Sharing…" : "Share to story"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={() => fileInput.current?.click()}
              aria-label="Pick a photo"
            >
              <IconPhoto className="size-5" />
            </Button>
            <Button
              type="button"
              size="lg"
              className="rounded-full"
              onClick={capture}
            >
              <IconCamera className="size-5" /> Capture
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
