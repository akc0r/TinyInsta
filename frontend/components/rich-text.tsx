import Link from "next/link"
import { Fragment } from "react"

// Render text with clickable #hashtags and @mentions.
//   #tag      → /hashtags/{tag}
//   @username → /search?q=username
export function RichText({ text }: { text: string }) {
  if (!text) return null
  const nodes: React.ReactNode[] = []
  let last = 0
  let key = 0

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
