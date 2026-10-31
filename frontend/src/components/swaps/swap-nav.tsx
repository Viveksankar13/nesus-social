"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Compass,
  Sparkles,
  Inbox,
  CalendarCheck,
  PlusCircle,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";

interface SwapNavProps {
  incomingCount?: number;
  activeSessionsCount?: number;
}

export function SwapNav({ incomingCount = 0, activeSessionsCount = 0 }: SwapNavProps) {
  const pathname = usePathname();

  const links = [
    {
      href: "/swaps",
      label: "Discovery Hub",
      icon: Compass,
      active: pathname === "/swaps",
    },
    {
      href: "/swaps/matches",
      label: "AI Matches",
      icon: Sparkles,
      active: pathname === "/swaps/matches",
    },
    {
      href: "/swaps/requests",
      label: "Proposals Inbox",
      icon: Inbox,
      active: pathname === "/swaps/requests",
      badge: incomingCount > 0 ? incomingCount : undefined,
    },
    {
      href: "/swaps/sessions",
      label: "My Sessions",
      icon: CalendarCheck,
      active: pathname === "/swaps/sessions" || pathname.startsWith("/swaps/sessions/"),
      badge: activeSessionsCount > 0 ? activeSessionsCount : undefined,
    },
  ];

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4 mb-6">
      <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all",
                link.active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{link.label}</span>
              {link.badge !== undefined && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500 text-white font-bold">
                  {link.badge}
                </span>
              )}
            </Link>
          );
        })}
      </div>

      <div className="flex items-center gap-2 self-end sm:self-auto">
        <Link
          href="/settings/swaps"
          className={cn(
            buttonVariants({ variant: "ghost", size: "sm" }),
            "h-8 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
          )}
          title="Swap Profile & Preferences"
        >
          <Settings className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Swap Preferences</span>
        </Link>

        <Link
          href="/swaps/new"
          className={cn(
            buttonVariants({ variant: "default", size: "sm" }),
            "h-8 text-xs gap-1.5 font-medium shadow-sm bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white"
          )}
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>Post Swap Offer</span>
        </Link>
      </div>
    </div>
  );
}
