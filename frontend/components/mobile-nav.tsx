"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  IconCompass,
  IconHome,
  IconSearch,
  IconSquareRoundedPlus,
  IconUser,
  type Icon,
} from "@tabler/icons-react"

import { cn } from "@/lib/utils"

const TABS: { label: string; icon: Icon; href: string }[] = [
  { label: "Home", icon: IconHome, href: "/" },
  { label: "Explore", icon: IconCompass, href: "/explore" },
  { label: "Create", icon: IconSquareRoundedPlus, href: "/upload" },
  { label: "Search", icon: IconSearch, href: "/search" },
  { label: "Profile", icon: IconUser, href: "/profile" },
]

export function MobileTopBar() {
  return (
    <header className="sticky top-0 z-30 flex h-12 items-center border-b bg-background px-4 md:hidden">
      <Link href="/" className="font-serif text-xl font-semibold italic">
        TinyInsta
      </Link>
    </header>
  )
}

export function MobileBottomNav() {
  const pathname = usePathname()
  return (
    <nav className="fixed inset-x-0 bottom-0 z-30 flex h-12 items-center justify-around border-t bg-background md:hidden">
      {TABS.map((tab, i) => {
        const Icon = tab.icon
        const active = tab.href === pathname
        return (
          <Link key={i} href={tab.href} className="p-2" aria-label={tab.label}>
            <Icon className="size-6" stroke={active ? 2.4 : 1.6} />
          </Link>
        )
      })}
    </nav>
  )
}
