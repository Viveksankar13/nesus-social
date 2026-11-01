"use client";

import * as React from "react";
import Image from "next/image";
import Link from "next/link";
import { LogOut, Repeat, Shield, Sparkles, User as UserIcon } from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { getInitials } from "@/lib/utils";

export function Navbar() {
  const { user, isAdmin, logout } = useAuth();

  return (
    <header className="fixed top-0 left-0 right-0 z-40 w-full border-b bg-background/90 backdrop-blur-md shadow-xs">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link
          href="/feed"
          className="flex items-center space-x-2.5 text-foreground font-bold text-lg tracking-tight hover:opacity-90 transition-opacity"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl overflow-hidden bg-primary/10 shadow-sm p-1">
            <Image
              src="/drupal.png"
              alt="Nexus Social Logo"
              width={32}
              height={32}
              className="h-7 w-7 object-contain"
              priority
            />
          </div>
          <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-primary to-indigo-500 bg-clip-text text-transparent">
            Nexus Social
          </span>
        </Link>

        {/* Right actions */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          <ThemeToggle />
          <NotificationBell />
          {user && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => {
                if (typeof window !== "undefined") {
                  window.dispatchEvent(new CustomEvent("open-ai-chat"));
                }
              }}
              className="h-9 w-9 text-muted-foreground hover:text-primary transition-colors touch-manipulation"
              title="Open Nexus AI"
              aria-label="Open Nexus AI"
            >
              <Sparkles className="h-4 w-4 text-primary" />
            </Button>
          )}

          {/* User menu */}
          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="relative h-9 w-9 rounded-full ring-offset-background transition-all hover:ring-2 hover:ring-primary/30"
                >
                  <Avatar className="h-9 w-9">
                    {user.avatar_url && (
                      <AvatarImage src={user.avatar_url} alt={user.display_name} />
                    )}
                    <AvatarFallback>{getInitials(user.display_name)}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-semibold leading-none text-foreground">
                      {user.display_name}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      @{user.username}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />

                <DropdownMenuItem asChild>
                  <Link href={`/profile/${user.username}`} className="cursor-pointer">
                    <UserIcon className="mr-2 h-4 w-4" />
                    <span>View Profile</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/settings/swaps" className="cursor-pointer">
                    <Repeat className="mr-2 h-4 w-4" />
                    <span>Swap Settings</span>
                  </Link>
                </DropdownMenuItem>

                {isAdmin && (
                  <DropdownMenuItem asChild>
                    <Link href="/admin" className="cursor-pointer text-primary">
                      <Shield className="mr-2 h-4 w-4" />
                      <span>Admin Console</span>
                    </Link>
                  </DropdownMenuItem>
                )}

                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => logout()}
                  className="cursor-pointer text-destructive focus:text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Sign Out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    </header>
  );
}
