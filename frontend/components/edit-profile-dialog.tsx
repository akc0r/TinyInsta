"use client"

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react"
import { IconCheck } from "@tabler/icons-react"

import {
  apiFetch,
  putToStorage,
  type Profile,
  type UploadTicket,
} from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { AvatarCropper } from "@/components/avatar-cropper"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

export function EditProfileDialog({
  profile,
  trigger,
  onSaved,
}: {
  profile: Profile
  trigger: ReactNode
  onSaved: (p: Profile) => void
}) {
  const { getToken } = useAuth()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(profile.name)
  const [username, setUsername] = useState(profile.username)
  const [bio, setBio] = useState(profile.bio)
  const [link, setLink] = useState(profile.link)
  const [avatarUrl, setAvatarUrl] = useState(profile.avatar_url)
  const [status, setStatus] = useState("")
  const [saving, setSaving] = useState(false)

  const fileInput = useRef<HTMLInputElement>(null)
  // Image picked from disk, awaiting crop.
  const [pickedFile, setPickedFile] = useState<File | null>(null)
  // Cropped result, kept until save (uploaded then), plus a local preview URL.
  const [croppedBlob, setCroppedBlob] = useState<Blob | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  // Release the object URL when it changes or the component unmounts.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  // Re-seed the form from the latest profile each time the dialog opens.
  function onOpenChange(next: boolean) {
    if (next) {
      setName(profile.name)
      setUsername(profile.username)
      setBio(profile.bio)
      setLink(profile.link)
      setAvatarUrl(profile.avatar_url)
      setCroppedBlob(null)
      setPreviewUrl(null)
      setStatus("")
    }
    setOpen(next)
  }

  function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) setPickedFile(f)
    e.target.value = "" // allow re-picking the same file
  }

  function onCropped(blob: Blob) {
    setPickedFile(null)
    setCroppedBlob(blob)
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(blob)
    })
  }

  // Push the cropped avatar to object storage via media-svc; returns its URL.
  async function uploadAvatar(blob: Blob): Promise<string> {
    const token = getToken()
    const ticketRes = await apiFetch("/media/upload-url", token, {
      method: "POST",
      body: JSON.stringify({ kind: "image" }),
    })
    if (!ticketRes.ok) throw new Error(`upload-url ${ticketRes.status}`)
    const ticket: UploadTicket = await ticketRes.json()

    const file = new File([blob], "avatar.jpg", { type: "image/jpeg" })
    const putRes = await putToStorage(ticket.upload_url, file)
    if (!putRes.ok) throw new Error(`storage PUT ${putRes.status}`)

    const mediaRes = await apiFetch("/media", token, {
      method: "POST",
      body: JSON.stringify({ media_id: ticket.media_id, kind: "image" }),
    })
    if (!mediaRes.ok) throw new Error(`media ${mediaRes.status}`)

    return ticket.object_url
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      let nextAvatarUrl = avatarUrl
      if (croppedBlob) {
        setStatus("Uploading photo…")
        nextAvatarUrl = await uploadAvatar(croppedBlob)
      }

      setStatus("Saving…")
      const res = await apiFetch("/users/me", getToken(), {
        method: "PATCH",
        body: JSON.stringify({
          name,
          username,
          bio,
          link,
          avatar_url: nextAvatarUrl,
        }),
      })
      if (res.ok) {
        onSaved(await res.json())
        setStatus("Saved")
        setOpen(false)
      } else if (res.status === 400) {
        setStatus("Username already taken or invalid input.")
      } else {
        setStatus(`Error ${res.status}`)
      }
    } catch (err) {
      setStatus(`Error: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit profile</DialogTitle>
          <DialogDescription>
            Update your details. They are visible to everyone.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center gap-4">
            <Avatar className="size-16">
              {(previewUrl || avatarUrl) && (
                <AvatarImage src={previewUrl || avatarUrl} alt={username} />
              )}
              <AvatarFallback className="text-xl">
                {(username || "?").charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 space-y-1.5">
              <Label>Profile photo</Label>
              <div>
                <input
                  ref={fileInput}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={onFilePicked}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileInput.current?.click()}
                >
                  {previewUrl ? "Change photo" : "Upload photo"}
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your full name"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="bio">Bio</Label>
            <Textarea
              id="bio"
              rows={3}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="link">Link</Label>
            <Input
              id="link"
              type="url"
              placeholder="https://yoursite.com"
              value={link}
              onChange={(e) => setLink(e.target.value)}
            />
          </div>

          <DialogFooter className="items-center">
            {status && (
              <span className="mr-auto flex items-center gap-1 text-sm text-muted-foreground">
                {status === "Saved" && (
                  <IconCheck className="size-4 text-green-600" />
                )}
                {status}
              </span>
            )}
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>

      <AvatarCropper
        file={pickedFile}
        open={!!pickedFile}
        onCancel={() => setPickedFile(null)}
        onCropped={onCropped}
      />
    </Dialog>
  )
}
