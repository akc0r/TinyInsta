"use client"

import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"

const VIEWPORT = 256 // on-screen crop square (px)
const OUTPUT = 320 // exported avatar size (px)
const MAX_ZOOM = 3

type Offset = { x: number; y: number }

// Square avatar cropper with drag-to-pan and zoom. Renders the chosen region to
// a canvas and hands back a JPEG blob — no external dependency.
export function AvatarCropper({
  file,
  open,
  onCancel,
  onCropped,
}: {
  file: File | null
  open: boolean
  onCancel: () => void
  onCropped: (blob: Blob) => void
}) {
  const [img, setImg] = useState<HTMLImageElement | null>(null)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState<Offset>({ x: 0, y: 0 })
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(
    null
  )

  // base scale so the image fully covers the viewport ("cover")
  const baseScale = img
    ? Math.max(VIEWPORT / img.naturalWidth, VIEWPORT / img.naturalHeight)
    : 1
  const scale = baseScale * zoom
  const dispW = img ? img.naturalWidth * scale : 0
  const dispH = img ? img.naturalHeight * scale : 0

  // Keep the image covering the viewport for the given displayed dimensions.
  function clampFor(o: Offset, w: number, h: number): Offset {
    return {
      x: Math.min(0, Math.max(VIEWPORT - w, o.x)),
      y: Math.min(0, Math.max(VIEWPORT - h, o.y)),
    }
  }
  const clamp = (o: Offset): Offset => clampFor(o, dispW, dispH)

  // Load the image whenever the file changes; center it.
  useEffect(() => {
    if (!file) return
    const url = URL.createObjectURL(file)
    const el = new Image()
    el.onload = () => {
      setImg(el)
      setZoom(1)
      const s = Math.max(
        VIEWPORT / el.naturalWidth,
        VIEWPORT / el.naturalHeight
      )
      setOffset({
        x: (VIEWPORT - el.naturalWidth * s) / 2,
        y: (VIEWPORT - el.naturalHeight * s) / 2,
      })
    }
    el.src = url
    return () => URL.revokeObjectURL(url)
  }, [file])

  // Re-clamp around the viewport center so the image keeps covering it on zoom.
  function onZoom(nextZoom: number) {
    if (!img) {
      setZoom(nextZoom)
      return
    }
    const nextScale = baseScale * nextZoom
    const cx = (VIEWPORT / 2 - offset.x) / scale // viewport-center in source px
    const cy = (VIEWPORT / 2 - offset.y) / scale
    setZoom(nextZoom)
    setOffset(
      clampFor(
        {
          x: VIEWPORT / 2 - cx * nextScale,
          y: VIEWPORT / 2 - cy * nextScale,
        },
        img.naturalWidth * nextScale,
        img.naturalHeight * nextScale
      )
    )
  }

  function onPointerDown(e: React.PointerEvent) {
    e.currentTarget.setPointerCapture(e.pointerId)
    drag.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y }
  }

  function onPointerMove(e: React.PointerEvent) {
    if (!drag.current) return
    setOffset(
      clamp({
        x: drag.current.ox + (e.clientX - drag.current.x),
        y: drag.current.oy + (e.clientY - drag.current.y),
      })
    )
  }

  function onPointerUp() {
    drag.current = null
  }

  function handleConfirm() {
    if (!img) return
    const canvas = document.createElement("canvas")
    canvas.width = OUTPUT
    canvas.height = OUTPUT
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    // Map the viewport window back to source-image pixels.
    const sx = -offset.x / scale
    const sy = -offset.y / scale
    const sSize = VIEWPORT / scale
    ctx.drawImage(img, sx, sy, sSize, sSize, 0, 0, OUTPUT, OUTPUT)
    canvas.toBlob(
      (blob) => {
        if (blob) onCropped(blob)
      },
      "image/jpeg",
      0.9
    )
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Crop photo</DialogTitle>
          <DialogDescription>
            Drag to reposition, zoom to fit.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center gap-4">
          <div
            className="relative touch-none overflow-hidden rounded-full bg-muted select-none"
            style={{ width: VIEWPORT, height: VIEWPORT }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          >
            {img && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={img.src}
                alt="crop"
                draggable={false}
                className="pointer-events-none absolute max-w-none origin-top-left cursor-grab"
                style={{
                  width: dispW,
                  height: dispH,
                  transform: `translate(${offset.x}px, ${offset.y}px)`,
                }}
              />
            )}
            <div className="pointer-events-none absolute inset-0 rounded-full ring-1 ring-white/40 ring-inset" />
          </div>

          <div className="w-full max-w-[256px] space-y-1.5">
            <Label htmlFor="zoom">Zoom</Label>
            <input
              id="zoom"
              type="range"
              min={1}
              max={MAX_ZOOM}
              step={0.01}
              value={zoom}
              onChange={(e) => onZoom(Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={!img}>
            Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
