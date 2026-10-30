"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  ArrowLeft,
  FileText,
  LayoutDashboard,
  Loader2,
  LogOut,
  Menu,
  Shield,
  ShieldAlert,
  Users,
} from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { apiClient } from "@/lib/api-client";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useToast } from "@/components/ui/use-toast";
import { cn, getInitials } from "@/lib/utils";
import type { StreamTokenResponse } from "@/types";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  {
    title: "Dashboard",
    href: "/admin",
    icon: LayoutDashboard,
  },
  {
    title: "Users",
    href: "/admin/users",
    icon: Users,
  },
  {
    title: "Content",
    href: "/admin/content",
    icon: FileText,
  },
  {
    title: "Moderation Queue",
    href: "/admin/moderation",
    icon: ShieldAlert,
  },
  {
    title: "Activity Logs",
    href: "/admin/activity",
    icon: Activity,
  },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading, isAdmin, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const { toast } = useToast();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  // 1. Role Guard: Redirect non-admins to /feed
  React.useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.replace("/login?redirect=" + encodeURIComponent(pathname));
      } else if (!isAdmin) {
        router.replace("/feed");
      }
    }
  }, [user, isLoading, isAdmin, router, pathname]);

  // 2. Real-Time Admin Alerts SSE stream
  React.useEffect(() => {
    if (!user || !isAdmin) return;

    let eventSource: EventSource | null = null;
    let isSubscribed = true;

    async function connectAdminSSE() {
      try {
        const tokenRes = await apiClient.post<StreamTokenResponse>(
          "/notifications/token"
        );
        if (!isSubscribed || !tokenRes.token) return;

        eventSource = new EventSource(
          `/api/v1/notifications/stream?token=${encodeURIComponent(tokenRes.token)}`
        );

        eventSource.addEventListener("admin_alert", (event) => {
          try {
            const data = JSON.parse(event.data);
            const notifType = data.type || "admin_alert";
            const payload = data.payload || {};

            toast({
              title:
                notifType === "admin_login"
                  ? "Security: Admin Login"
                  : notifType === "moderation" || notifType === "flagged"
                  ? "Moderation Alert"
                  : "Admin Security Alert",
              description:
                payload.message ||
                `Event received on admin channel from ${payload.username || payload.ip || "system"}.`,
              variant: notifType === "moderation" ? "destructive" : "default",
            });
          } catch {
            // Ignore parse errors on heartbeat
          }
        });

        eventSource.onerror = () => {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
        };
      } catch {
        // Silent catch for stream token failures
      }
    }

    connectAdminSSE();

    return () => {
      isSubscribed = false;
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [user, isAdmin, toast]);

  if (isLoading || !isAdmin || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm">Verifying administrative credentials...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-muted/20">
      {/* Desktop Dark Sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border/80 bg-zinc-950 text-zinc-100 md:flex">
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-zinc-800/80 px-6">
          <Link href="/admin" className="flex items-center gap-2.5 font-bold tracking-tight">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-md">
              <Shield className="h-4 w-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-wide text-white">NEXUS ADMIN</span>
              <span className="text-[10px] uppercase tracking-wider text-indigo-400">Control Console</span>
            </div>
          </Link>
          <Badge variant="outline" className="border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-[10px] px-1.5 py-0">
            PROD
          </Badge>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 space-y-1 px-3 py-4">
          <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
            Management
          </p>
          {navItems.map((item) => {
            const isActive =
              item.href === "/admin"
                ? pathname === "/admin"
                : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
                )}
              >
                <Icon className={cn("h-4 w-4 shrink-0", isActive ? "text-white" : "text-zinc-400")} />
                {item.title}
              </Link>
            );
          })}
        </div>

        {/* Bottom Quick Switch & Profile */}
        <div className="border-t border-zinc-800/80 p-3 space-y-2">
          <Link
            href="/feed"
            className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium text-zinc-400 transition-colors hover:bg-zinc-900 hover:text-zinc-100"
          >
            <ArrowLeft className="h-4 w-4 text-zinc-400" />
            Back to User Feed
          </Link>

          <div className="flex items-center justify-between rounded-md bg-zinc-900/80 p-2.5">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <Avatar className="h-7 w-7 border border-zinc-700">
                <AvatarImage src={user.avatar_url ?? undefined} alt={user.display_name} />
                <AvatarFallback className="bg-indigo-950 text-indigo-200 text-xs">
                  {getInitials(user.display_name)}
                </AvatarFallback>
              </Avatar>
              <div className="truncate text-left text-xs">
                <p className="font-semibold text-zinc-100 truncate">{user.display_name}</p>
                <p className="text-[10px] text-zinc-400 truncate">@{user.username}</p>
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => logout()}
              className="h-7 w-7 text-zinc-400 hover:bg-zinc-800 hover:text-rose-400"
              title="Logout"
            >
              <LogOut className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border/80 bg-background/95 px-4 backdrop-blur-md sm:px-8">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              <Menu className="h-5 w-5" />
            </Button>

            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Shield className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              <span className="font-semibold text-foreground">Console</span>
              <span>/</span>
              <span className="capitalize">
                {pathname === "/admin"
                  ? "Dashboard"
                  : pathname.split("/admin/")[1]?.replace("-", " ") || "Overview"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="outline" className="hidden sm:flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 border-emerald-500/20 bg-emerald-500/10">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              Live SSE Active
            </Badge>

            <ThemeToggle />
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="border-b border-zinc-800 bg-zinc-950 p-4 text-zinc-100 md:hidden">
            <div className="space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium",
                    pathname === item.href
                      ? "bg-indigo-600 text-white"
                      : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.title}
                </Link>
              ))}
              <Link
                href="/feed"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to User Feed
              </Link>
            </div>
          </div>
        )}

        {/* Page Content Body */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
