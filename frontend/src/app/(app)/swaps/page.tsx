"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  Compass,
  GraduationCap,
  MapPin,
  Repeat,
  Settings,
  Shield,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { swapApi } from "@/lib/swap-api";

export default function SwapsHomePage() {
  const { data: profile } = useQuery({
    queryKey: ["swap-profile", "me"],
    queryFn: swapApi.getMyProfile,
  });

  const { data: taxonomy = [] } = useQuery({
    queryKey: ["swap-taxonomy"],
    queryFn: swapApi.getTaxonomy,
  });

  const hasOnboarded =
    profile &&
    profile.is_18_confirmed &&
    (profile.teach_skills.length > 0 || profile.learn_skills.length > 0);

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl border bg-gradient-to-r from-primary/10 via-purple-500/5 to-rose-500/10 p-6 sm:p-10 shadow-sm">
        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-semibold backdrop-blur-sm">
            <Repeat className="h-3.5 w-3.5" />
            <span>Hyper-Local Skill Swap Economy</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Exchange 30 Minutes of Peer Help.{" "}
            <span className="bg-gradient-to-r from-primary to-rose-500 bg-clip-text text-transparent">
              Zero Money Involved.
            </span>
          </h1>

          <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
            Connect with peers nearby or remotely to barter mentorship: teach what you know,
            learn what you want. Safe, private, and 100% reciprocal.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            {!hasOnboarded ? (
              <Button asChild size="lg" className="gap-2 shadow-sm">
                <Link href="/swaps/onboarding">
                  <Sparkles className="h-4 w-4" />
                  <span>Start 4-Step Onboarding</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            ) : (
              <Button asChild size="lg" className="gap-2 shadow-sm">
                <Link href="/settings/swaps">
                  <Settings className="h-4 w-4" />
                  <span>Manage Swap Preferences</span>
                </Link>
              </Button>
            )}

            <Button asChild variant="outline" size="lg" className="gap-2">
              <Link href="/swaps/onboarding">
                <GraduationCap className="h-4 w-4" />
                <span>Update Skills & Availability</span>
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* User Status Bar if Onboarded */}
      {hasOnboarded && profile && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-5 rounded-2xl border bg-card shadow-sm">
          <div className="space-y-1">
            <span className="text-xs text-muted-foreground uppercase font-semibold">
              Trust Score
            </span>
            <div className="flex items-center gap-1.5">
              <Shield className="h-4 w-4 text-primary" />
              <span className="text-xl font-bold">{profile.trust_score}</span>
              <span className="text-xs text-muted-foreground">/ 100</span>
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-muted-foreground uppercase font-semibold">
              Location Area
            </span>
            <div className="flex items-center gap-1.5 truncate">
              <MapPin className="h-4 w-4 text-rose-500 shrink-0" />
              <span className="text-sm font-semibold truncate">
                {profile.area_label || "Remote Only"}
              </span>
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-muted-foreground uppercase font-semibold">
              Skills I Teach
            </span>
            <div className="flex items-center gap-1.5">
              <GraduationCap className="h-4 w-4 text-green-500" />
              <span className="text-xl font-bold">{profile.teach_skills.length}</span>
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-muted-foreground uppercase font-semibold">
              Skills I Learn
            </span>
            <div className="flex items-center gap-1.5">
              <BookOpen className="h-4 w-4 text-blue-500" />
              <span className="text-xl font-bold">{profile.learn_skills.length}</span>
            </div>
          </div>
        </div>
      )}

      {/* Core Principles Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl border bg-card space-y-3 shadow-xs">
          <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
            <Repeat className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-base">Pure Reciprocity</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Strictly non-monetary. Swaps are divided into two equal 30-minute halves so both
            parties give and receive knowledge fairly.
          </p>
        </div>

        <div className="p-6 rounded-2xl border bg-card space-y-3 shadow-xs">
          <div className="h-10 w-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-600">
            <Compass className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-base">Privacy-by-Design</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Coarse coordinates (~1 km resolution) and distance buckets only. Exact locations
            and geohashes are never exposed. In-person meetups occur in public places.
          </p>
        </div>

        <div className="p-6 rounded-2xl border bg-card space-y-3 shadow-xs">
          <div className="h-10 w-10 rounded-xl bg-rose-500/10 flex items-center justify-center text-rose-600">
            <Shield className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-base">Trust & Safety</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Double-blind review system, AI moderation preventing payment solicitation,
            and mutual blocking protect our learning community.
          </p>
        </div>
      </div>

      {/* Canonical Taxonomy Explorer */}
      <div className="space-y-4 p-6 rounded-2xl border bg-card shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-bold">Canonical Skills Directory</h2>
          </div>
          <span className="text-xs text-muted-foreground">
            {taxonomy.length} categories available
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-2">
          {taxonomy.map((group) => (
            <div
              key={group.category}
              className="p-4 rounded-xl border bg-muted/20 space-y-2.5"
            >
              <h4 className="font-bold text-sm text-foreground flex items-center justify-between">
                <span>{group.category}</span>
                <span className="text-[10px] text-muted-foreground font-normal">
                  {group.skills.length} skills
                </span>
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {group.skills.map((s) => (
                  <span
                    key={s.id}
                    className="inline-block text-[11px] px-2 py-0.5 rounded-md bg-card border text-muted-foreground"
                  >
                    {s.display_name}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
