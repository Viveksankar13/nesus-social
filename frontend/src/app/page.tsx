"use client";

import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Bot,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Rss,
  Shield,
  ShieldAlert,
  Zap,
} from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { getInitials } from "@/lib/utils";

export default function LandingPage() {
  const { user, isAdmin, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-background via-muted/20 to-background">
      {/* Navigation Bar */}
      <header className="border-b bg-background/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href={user ? (isAdmin ? "/admin" : "/feed") : "/"} className="flex items-center space-x-2.5">
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

          <div className="flex items-center space-x-3">
            <ThemeToggle />

            {user ? (
              <div className="flex items-center space-x-2">
                {isAdmin ? (
                  <Link href="/admin">
                    <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm gap-1.5">
                      <Shield className="h-4 w-4" />
                      <span>Admin Console</span>
                    </Button>
                  </Link>
                ) : null}

                <Link href="/feed">
                  <Button variant="outline" size="sm" className="gap-1.5">
                    <Rss className="h-4 w-4" />
                    <span>Feed</span>
                  </Button>
                </Link>

                <div className="hidden sm:flex items-center gap-2 pl-2 border-l">
                  <Avatar className="h-8 w-8">
                    {user.avatar_url && <AvatarImage src={user.avatar_url} alt={user.display_name} />}
                    <AvatarFallback>{getInitials(user.display_name)}</AvatarFallback>
                  </Avatar>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => logout()}
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    title="Sign Out"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="ghost" size="sm">
                    Sign In
                  </Button>
                </Link>
                <Link href="/register">
                  <Button size="sm" className="shadow-sm">
                    Get Started
                    <ArrowRight className="ml-1.5 h-4 w-4" />
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-5xl mx-auto px-4 py-16 sm:py-24 text-center">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold tracking-wide uppercase mb-6">
          <Zap className="h-3.5 w-3.5" />
          <span>Next-Generation AI Social Network</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-foreground max-w-4xl mx-auto leading-tight sm:leading-none">
          Connect, Create, and Discover with{" "}
          <span className="bg-gradient-to-r from-primary via-indigo-500 to-purple-600 bg-clip-text text-transparent">
            Precision Intelligence
          </span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto">
          Nexus Social combines lightning-fast social feeds with Google Gemini 2.5 AI.
          Draft captivating posts in seconds, summarize vibrant discussions, and engage with smart replies.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          {user ? (
            isAdmin ? (
              <>
                <Link href="/admin" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full sm:w-auto px-8 shadow-md bg-indigo-600 hover:bg-indigo-700 text-white gap-2">
                    <LayoutDashboard className="h-5 w-5" />
                    Enter Admin Console
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Button>
                </Link>
                <Link href="/feed" className="w-full sm:w-auto">
                  <Button variant="outline" size="lg" className="w-full sm:w-auto px-8 gap-2">
                    <Rss className="h-5 w-5" />
                    View Community Feed
                  </Button>
                </Link>
              </>
            ) : (
              <>
                <Link href="/feed" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full sm:w-auto px-8 shadow-md gap-2">
                    <Rss className="h-5 w-5" />
                    Go to Your Feed
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Button>
                </Link>
                <Link href={`/profile/${user.username}`} className="w-full sm:w-auto">
                  <Button variant="outline" size="lg" className="w-full sm:w-auto px-8">
                    View Your Profile
                  </Button>
                </Link>
              </>
            )
          ) : (
            <>
              <Link href="/register" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto px-8 shadow-md">
                  Create Free Account
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/login" className="w-full sm:w-auto">
                <Button variant="outline" size="lg" className="w-full sm:w-auto px-8">
                  Sign In to Your Feed
                </Button>
              </Link>
            </>
          )}
        </div>

        {/* Feature Grid */}
        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="rounded-2xl border bg-card p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
              <Bot className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold">AI Post Composer</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Generate 3 distinct variants tailored to casual, professional, funny, or inspirational tones with a single click.
            </p>
          </div>

          <div className="rounded-2xl border bg-card p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
              <MessageSquare className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold">Smart Thread Summaries</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Instantly extract key takeaways and audience sentiment from active community discussions and nested comment trees.
            </p>
          </div>

          <div className="rounded-2xl border bg-card p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold">Proactive Safety</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Multi-tiered automated safety guards evaluate content in the background, keeping discourse respectful and constructive.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        <p>&copy; {new Date().getFullYear()} Nexus Social. Built with Next.js 14, FastAPI & Google Gemini.</p>
      </footer>
    </div>
  );
}
