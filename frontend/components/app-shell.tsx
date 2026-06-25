import { AppSidebar } from "@/components/app-sidebar"
import { MobileBottomNav, MobileTopBar } from "@/components/mobile-nav"

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-svh">
      <AppSidebar />
      <MobileTopBar />
      <main className="min-h-svh pb-12 md:pb-0 md:pl-[72px] xl:pl-[245px]">
        {children}
      </main>
      <MobileBottomNav />
    </div>
  )
}
