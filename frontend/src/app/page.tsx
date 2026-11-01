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
import { useState } from "react";
import CursorRingField from "@/components/originkit/ui/cursor-ring-field";
import LanyardBadge from "@/components/podie/kedhareswer--lanyard-badge/components/ui/lanyard-badge";
import { SpotlightFeatureCard } from "@/components/ui/spotlight-card/spotlight-feature-card";

export default function LandingPage() {
  const { user, isAdmin, logout } = useAuth();
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-background via-muted/20 to-background">
      {/* Navigation Bar — fixed top so it hovers reliably while scrolling */}
      <header className="border-b bg-background/90 backdrop-blur-md fixed top-0 left-0 right-0 z-50 shadow-xs">
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
      {/* Spacer so fixed header never covers content */}
      <div className="h-16 shrink-0" aria-hidden="true" />

      {/* Hero Section — cursor ring is the background layer */}
      <main className="flex-1 relative overflow-hidden">
        {/* WebGL cursor ring field — covers only this hero section */}
        <div className="absolute inset-0 z-0">
          <CursorRingField
            style={{ width: "100%", height: "100%" }}
            background="transparent"
            colors={{ items: ["#7189ff", "#4f46e5", "#0b0b18"] }}
            ring={{ radius: 12, width: 9, push: 50, turbulence: 100 }}
            density={260}
            dotSize={110}
            speed={6}
          />
        </div>

        {/* Content sits above the ring */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 pt-0 pb-16 sm:pb-24">

          {/* Two-column: on small screens, badge comes first (flex-col-reverse), on lg screens text on left, badge on right */}
          <div className="flex flex-col-reverse lg:flex-row items-center gap-6 lg:gap-12">

            {/* ── LEFT: Hero text ── */}
            <div className="flex-1 text-left w-full">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold tracking-wide uppercase mb-6">
                <Zap className="h-3.5 w-3.5" />
                <span>Next-Generation AI Social Network</span>
              </div>

              <h1 className="text-4xl sm:text-5xl xl:text-6xl font-extrabold tracking-tight text-foreground max-w-2xl leading-tight">
                Connect, Create, and Discover with AI and{" "}
                <span className="bg-gradient-to-r from-primary via-indigo-500 to-purple-600 bg-clip-text text-transparent">
                  Swap Skills
                </span>
              </h1>

              <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-xl">
                Nexus Social combines lightning-fast social feeds with AI.
                Draft captivating posts in seconds, summarize vibrant discussions, and smartly learn new skills from peers.
              </p>

              <div className="mt-10 flex flex-col sm:flex-row items-start gap-4">
                {user ? (
                  isAdmin ? (
                    <>
                      <Link href="/admin">
                        <Button size="lg" className="px-8 shadow-md bg-indigo-600 hover:bg-indigo-700 text-white gap-2">
                          <LayoutDashboard className="h-5 w-5" />
                          Enter Admin Console
                          <ArrowRight className="ml-1 h-4 w-4" />
                        </Button>
                      </Link>
                      <Link href="/feed">
                        <Button variant="outline" size="lg" className="px-8 gap-2">
                          <Rss className="h-5 w-5" />
                          View Community Feed
                        </Button>
                      </Link>
                    </>
                  ) : (
                    <>
                      <Link href="/feed">
                        <Button size="lg" className="px-8 shadow-md gap-2">
                          <Rss className="h-5 w-5" />
                          Go to Your Feed
                          <ArrowRight className="ml-1 h-4 w-4" />
                        </Button>
                      </Link>
                      <Link href={`/profile/${user.username}`}>
                        <Button variant="outline" size="lg" className="px-8">
                          View Your Profile
                        </Button>
                      </Link>
                    </>
                  )
                ) : (
                  <>
                    <Link href="/register">
                      <Button size="lg" className="px-8 shadow-md">
                        Create Free Account
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </Button>
                    </Link>
                    <Link href="/login">
                      <Button variant="outline" size="lg" className="px-8">
                        Sign In to Your Feed
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </div>

            {/* ── RIGHT (or TOP on mobile/tab): Lanyard Badge ── */}
            <div className="flex-shrink-0 w-full sm:w-[380px] lg:w-[420px] xl:w-[480px] flex justify-center overflow-visible">
              <LanyardBadge
                title="Nexus Social"
                subtitle="AI Social Network · 2026"
                name="Connect & Discover"
                role="Powered by Gemini 2.5"
                strapText="nexus social"
                strapLabel="AI NETWORK 2026"
                strapColor="#1e1b4b"
                inkColor="#818cf8"
                cardColor="#f0f0ff"
                cardWidth={220}
                className="h-[460px] sm:h-[500px] lg:h-[540px]"
                flipButton={false}
              />
            </div>

          </div>

          {/* Feature Grid with Spotlight 3D Tilt and Focus-Dimming Effect */}
          <div className="mt-14 sm:mt-20 grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 text-left max-w-md md:max-w-none mx-auto">
            <SpotlightFeatureCard
              icon={Bot}
              title="AI Post Composer"
              description="Generate 3 distinct variants tailored to casual, professional, funny, or inspirational tones with a single click."
              color="#6366f1"
              dimmed={hoveredCard !== null && hoveredCard !== "composer"}
              onHoverStart={() => setHoveredCard("composer")}
              onHoverEnd={() => setHoveredCard(null)}
            />

            <SpotlightFeatureCard
              icon={MessageSquare}
              title="Smart Thread Summaries"
              description="Instantly extract key takeaways and audience sentiment from active community discussions and nested comment trees."
              color="#8b5cf6"
              dimmed={hoveredCard !== null && hoveredCard !== "summaries"}
              onHoverStart={() => setHoveredCard("summaries")}
              onHoverEnd={() => setHoveredCard(null)}
            />

            <SpotlightFeatureCard
              icon={ShieldAlert}
              title="Proactive Safety"
              description="Multi-tiered automated safety guards evaluate content in the background, keeping discourse respectful and constructive."
              color="#ec4899"
              dimmed={hoveredCard !== null && hoveredCard !== "safety"}
              onHoverStart={() => setHoveredCard("safety")}
              onHoverEnd={() => setHoveredCard(null)}
            />
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
