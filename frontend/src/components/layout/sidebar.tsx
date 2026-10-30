"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Home, Shield, User as UserIcon } from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  const { user, isAdmin } = useAuth();

  const navItems = [
    {
      label: "Feed",
      href: "/feed",
      icon: Home,
      active: pathname === "/feed",
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
    <>
      {/* Desktop sidebar */}
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
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </aside>

      {/* Mobile bottom navigation bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur-md px-4 py-2 flex items-center justify-around">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center p-2 rounded-lg text-xs font-medium transition-colors",
                item.active ? "text-primary" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="h-5 w-5" />
              <span className="mt-1 text-[11px]">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
