"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Home, MessageSquare, Repeat, Shield, Sparkles, User as UserIcon, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/contexts/auth-context";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  const { user, isAdmin } = useAuth();

  const { data: unreadData } = useQuery<{ unread_count: number }>({
    queryKey: ["messages", "unread-count"],
    queryFn: () => apiClient.get<{ unread_count: number }>("/messages/unread-count"),
    enabled: !!user,
    refetchInterval: 5000,
  });
  const unreadCount = unreadData?.unread_count || 0;

  const navItems = [
    {
      label: "Feed",
      href: "/feed",
      icon: Home,
      active: pathname === "/feed",
    },
    {
      label: "Skill Swaps",
      href: "/swaps",
      icon: Repeat,
      active: pathname.startsWith("/swaps"),
    },
    {
      label: "Messages",
      href: "/messages",
      icon: MessageSquare,
      active: pathname.startsWith("/messages"),
      badge: unreadCount,
    },
    {
      label: "Friends",
      href: "/friends",
      icon: Users,
      active: pathname.startsWith("/friends"),
    },
    {
      label: "Notifications",
      href: "/notifications",
      icon: Bell,
      active: pathname === "/notifications",
    },
    {
      label: "Profile",
      href: user ? `/profile/${user.username}` : "/profile",
      icon: UserIcon,
      active: pathname.startsWith("/profile"),
    },
  ];

  if (isAdmin) {
    navItems.push({
      label: "Admin Console",
      href: "/admin",
      icon: Shield,
      active: pathname.startsWith("/admin"),
    });
  }

  return (
    /* Desktop sidebar */
    <aside className="hidden md:flex flex-col w-56 shrink-0 py-6 pr-4 space-y-1">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              item.active
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="flex-1">{item.label}</span>
            {item.badge !== undefined && item.badge > 0 && (
              <span className="ml-auto inline-flex items-center justify-center h-5 min-w-5 px-1.5 text-[10px] font-bold bg-primary text-primary-foreground rounded-full">
                {item.badge}
              </span>
            )}
          </Link>
        );
      })}
    </aside>
  );
}

/**
 * MobileNavBar — comes along when scrolling at the bottom of the screen,
 * styled with a sleek backdrop blur and touch targets. Generous bottom clearance
 * on <main> ensures it NEVER overlaps or covers post content.
 */
export function MobileNavBar() {
  const pathname = usePathname();
  const { user, isAdmin } = useAuth();

  const { data: unreadData } = useQuery<{ unread_count: number }>({
    queryKey: ["messages", "unread-count"],
    queryFn: () => apiClient.get<{ unread_count: number }>("/messages/unread-count"),
    enabled: !!user,
    refetchInterval: 5000,
  });
  const unreadCount = unreadData?.unread_count || 0;

  const navItems = [
    {
      label: "Feed",
      href: "/feed",
      icon: Home,
      active: pathname === "/feed",
    },
    {
      label: "Swaps",
      href: "/swaps",
      icon: Repeat,
      active: pathname.startsWith("/swaps"),
    },
    {
      label: "Messages",
      href: "/messages",
      icon: MessageSquare,
      active: pathname.startsWith("/messages"),
      badge: unreadCount,
    },
    {
      label: "Friends",
      href: "/friends",
      icon: Users,
      active: pathname.startsWith("/friends"),
    },
    {
      label: "Notifs",
      href: "/notifications",
      icon: Bell,
      active: pathname === "/notifications",
    },
    {
      label: "Profile",
      href: user ? `/profile/${user.username}` : "/profile",
      icon: UserIcon,
      active: pathname.startsWith("/profile"),
    },
  ];

  if (isAdmin) {
    navItems.push({
      label: "Admin",
      href: "/admin",
      icon: Shield,
      active: pathname.startsWith("/admin"),
    });
  }

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border/80 bg-background/90 backdrop-blur-xl px-2 pt-1.5 shadow-lg touch-manipulation"
      style={{ paddingBottom: "max(0.6rem, env(safe-area-inset-bottom, 12px))" }}
      aria-label="Mobile Navigation"
    >
      <div
        className={cn(
          "grid gap-1 text-center max-w-lg mx-auto",
          navItems.length === 7 ? "grid-cols-7" : "grid-cols-6"
        )}
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center py-1.5 px-1 rounded-xl text-[10px] font-medium transition-all active:scale-95 touch-manipulation",
                item.active
                  ? "bg-primary/15 text-primary font-bold shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <div className="relative">
                <Icon className="h-4.5 w-4.5" />
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="absolute -top-1 -right-2 inline-flex items-center justify-center h-3.5 min-w-3.5 px-1 text-[8px] font-bold bg-primary text-primary-foreground rounded-full">
                    {item.badge}
                  </span>
                )}
              </div>
              <span className="mt-1 truncate max-w-full leading-none">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export const MobileSectionFooter = MobileNavBar;
