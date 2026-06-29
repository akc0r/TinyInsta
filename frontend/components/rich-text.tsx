import Link from "next/link"
import { Fragment } from "react"

// Render text with clickable #hashtags and @mentions.
//   #tag      → /hashtags/{tag}   (search-svc hashtag page)
//   @username → /search?q=username (mentions aren't resolvable to an id here)
// Everything else is rendered verbatim, newlines preserved by the caller's CSS.

export function RichText({ text }: { text: string }) {
  if (!text) return null
  const nodes: React.ReactNode[] = []
  let last = 0
  let key = 0

  // matchAll over a fresh global regex — no shared lastIndex to mutate.
  for (const m of text.matchAll(/([#@])(\w+)/g)) {
    const index = m.index ?? 0
    if (index > last) {
      nodes.push(<Fragment key={key++}>{text.slice(last, index)}</Fragment>)
    }
    const [, sigil, word] = m
    const href =
      sigil === "#" ? `/hashtags/${word.toLowerCase()}` : `/search?q=${word}`
    nodes.push(
      <Link key={key++} href={href} className="text-primary hover:underline">
        {sigil}
        {word}
      </Link>
    )
    last = index + m[0].length
  }
  if (last < text.length) {
    nodes.push(<Fragment key={key++}>{text.slice(last)}</Fragment>)
  }
  return <>{nodes}</>
}
