"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  IconCompass,
  IconHeart,
  IconHome,
  IconLogin2,
  IconLogout,
  IconMenu2,
  IconMessageCircle,
  IconPhoto,
  IconSearch,
  IconSquareRoundedPlus,
  IconUser,
  type Icon,
} from "@tabler/icons-react"

import { useAuth } from "@/lib/auth-context"
import { useNotifications } from "@/lib/use-realtime"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

type NavItem = {
  label: string
  icon: Icon
  href?: string
  disabled?: boolean
}

const NAV: NavItem[] = [
  { label: "Home", icon: IconHome, href: "/" },
  { label: "Search", icon: IconSearch, href: "/search" },
  { label: "Explore", icon: IconCompass, href: "/explore" },
  { label: "Messages", icon: IconMessageCircle, disabled: true },
  { label: "Notifications", icon: IconHeart, href: "/notifications" },
  { label: "Create", icon: IconSquareRoundedPlus, href: "/upload" },
  { label: "Profile", icon: IconUser, href: "/profile" },
]

function NavLink({
  item,
  active,
  badge = 0,
}: {
  item: NavItem
  active: boolean
  badge?: number
}) {
  const Icon = item.icon
  const inner = (
    <>
      <span className="relative shrink-0">
        <Icon className="size-6" stroke={active ? 2.4 : 1.6} />
        {badge > 0 && (
          <span className="absolute -top-1.5 -right-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {badge > 9 ? "9+" : badge}
          </span>
        )}
      </span>
      <span className={cn("hidden xl:inline", active && "font-semibold")}>
        {item.label}
      </span>
    </>
  )
  const base =
    "flex items-center gap-4 rounded-lg p-3 text-base transition-colors hover:bg-accent xl:w-full"

  if (item.href && !item.disabled) {
    return (
      <Link href={item.href} className={cn(base, active && "font-semibold")}>
        {inner}
      </Link>
    )
  }
  return (
    <button
      type="button"
      title={`${item.label} — coming soon`}
      className={cn(base, "cursor-default text-muted-foreground/80")}
    >
      {inner}
    </button>
  )
}

export function AppSidebar() {
  const pathname = usePathname()
  const { ready, authenticated, login, logout } = useAuth()
  const { unread } = useNotifications(ready && authenticated)

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[72px] flex-col border-r bg-background px-3 py-5 md:flex xl:w-[245px]">
      <Link href="/" className="mb-8 flex items-center gap-2 p-3">
        <IconPhoto className="size-7 xl:hidden" />
        <span className="hidden font-serif text-2xl font-semibold tracking-tight italic xl:inline">
          TinyInsta
        </span>
      </Link>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV.map((item) => (
          <NavLink
            key={item.label}
            item={item}
            active={item.href === pathname}
            badge={item.label === "Notifications" ? unread : 0}
          />
        ))}
      </nav>

      <div className="mt-auto">
        {ready &&
          (authenticated ? (
            <Button
              variant="ghost"
              onClick={logout}
              className="h-auto w-full justify-start gap-4 p-3 text-base font-normal"
            >
              <IconLogout className="size-6 shrink-0" stroke={1.6} />
              <span className="hidden xl:inline">Log out</span>
            </Button>
          ) : (
            <Button
              variant="ghost"
              onClick={login}
              className="h-auto w-full justify-start gap-4 p-3 text-base font-normal"
            >
              <IconLogin2 className="size-6 shrink-0" stroke={1.6} />
              <span className="hidden xl:inline">Log in</span>
            </Button>
          ))}
        <div className="flex items-center gap-4 rounded-lg p-3 text-base text-muted-foreground/80">
          <IconMenu2 className="size-6 shrink-0" stroke={1.6} />
          <span className="hidden xl:inline">More</span>
        </div>
      </div>
    </aside>
  )
}
