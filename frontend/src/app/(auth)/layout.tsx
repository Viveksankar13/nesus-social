"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { ThemeToggle } from "@/components/ui/theme-toggle";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen flex flex-col justify-between bg-gradient-to-b from-background via-muted/20 to-background p-4 sm:p-8">
      {/* Top Header */}
      <div className="flex items-center justify-between w-full max-w-6xl mx-auto py-2">
        <Link
          href="/"
          className="flex items-center space-x-2 text-foreground font-bold text-lg tracking-tight hover:opacity-90 transition-opacity"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <span className="bg-gradient-to-r from-primary to-indigo-500 bg-clip-text text-transparent font-extrabold text-xl">
            Nexus Social
          </span>
        </Link>
        <ThemeToggle />
      </div>

      {/* Main Form Centerpiece */}
      <div className="flex-1 flex items-center justify-center py-8">
        <div className="w-full max-w-md">{children}</div>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-muted-foreground py-4">
        &copy; {new Date().getFullYear()} Nexus Social. Built with precision and intelligence.
      </div>
    </div>
  );
}
