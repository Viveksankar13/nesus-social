"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  GraduationCap,
  Info,
  Loader2,
  MapPin,
  Repeat,
  Sparkles,
} from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { swapApi } from "@/lib/swap-api";
import { SwapMatchResponse } from "@/types/swap";
import { SwapNav } from "@/components/swaps/swap-nav";

export default function SwapMatchesPage() {
  const { data: matches = [], isLoading } = useQuery({
    queryKey: ["swap-matches"],
    queryFn: () => swapApi.getMatches(15),
  });

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      <SwapNav />

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Link href="/swaps" className="hover:text-foreground flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Swaps Discovery</span>
        </Link>
      </div>

      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-r from-indigo-500/10 via-purple-500/5 to-transparent p-6 sm:p-8 space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 text-xs font-semibold backdrop-blur-sm">
          <Sparkles className="w-3.5 h-3.5" />
          <span>AI-Powered Recommendations</span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
          Personalized Matches for You
        </h1>

        <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">
          Ranked by our transparent 5-criteria matching engine: mutual skill match (35%),
          proximity & remote mode (25%), availability overlap (20%), peer trust (15%), and freshness (5%).
        </p>
      </div>

      {isLoading ? (
        <div className="py-16 text-center space-y-3">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
          <p className="text-sm text-muted-foreground">
            Evaluating skill alignment and generating AI match insights...
          </p>
        </div>
      ) : matches.length === 0 ? (
        <div className="text-center py-16 border rounded-3xl bg-card p-8 space-y-4 shadow-sm">
          <Repeat className="w-12 h-12 text-muted-foreground mx-auto opacity-50" />
          <h3 className="text-lg font-semibold text-foreground">No matches found yet</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Make sure you have declared your teaching and learning skills in your profile so our engine can find mutual swap partners.
          </p>
          <Button asChild className="gap-2">
            <Link href="/settings/swaps">
              <span>Update My Skills & Availability</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          {matches.map((item: SwapMatchResponse) => {
            const percentage = Math.round(item.match_score * 100);
            const { listing, explanation, score_breakdown } = item;

            return (
              <Card
                key={listing.id}
                className="rounded-2xl border-border hover:border-primary/50 transition-all shadow-sm overflow-hidden"
              >
                <CardHeader className="p-5 pb-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <Link
                        href={`/profile/${listing.user.username}`}
                        className="flex items-center gap-2 group"
                      >
                        <Avatar className="w-9 h-9">
                          {listing.user.avatar_url && (
                            <AvatarImage src={listing.user.avatar_url} />
                          )}
                          <AvatarFallback className="text-xs">
                            {listing.user.display_name.slice(0, 2).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors">
                            {listing.user.display_name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            @{listing.user.username}
                          </div>
                        </div>
                      </Link>

                      <Badge
                        variant="outline"
                        className="text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1 border-muted-foreground/30"
                      >
                        <MapPin className="w-3 h-3 text-indigo-500" />
                        <span>{listing.distance_bucket || "remote"}</span>
                      </Badge>
                    </div>

                    {/* Match Score Badge */}
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-indigo-500/15 to-purple-500/15 border border-indigo-500/30">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                      <span className="text-sm font-extrabold text-foreground">
                        {percentage}% Match
                      </span>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="px-5 pb-4 space-y-4">
                  {/* AI "Why You Match" Explanation Pill */}
                  <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3 flex items-start gap-2.5 text-xs">
                    <Sparkles className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-foreground block text-[11px] uppercase tracking-wider mb-0.5">
                        Why you match
                      </span>
                      <p className="text-foreground leading-relaxed font-medium">
                        {explanation}
                      </p>
                    </div>
                  </div>

                  {/* Listing Title & Skills */}
                  <div className="space-y-2">
                    <h3 className="text-base font-bold text-foreground">
                      {listing.title}
                    </h3>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 flex items-center gap-2">
                        <GraduationCap className="w-4 h-4 shrink-0" />
                        <span>
                          <strong>Teaches:</strong> {listing.skill_offered.display_name}
                        </span>
                      </div>
                      <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-700 dark:text-indigo-300 flex items-center gap-2">
                        <BookOpen className="w-4 h-4 shrink-0" />
                        <span>
                          <strong>Wants:</strong>{" "}
                          {listing.skill_wanted?.display_name || "Open to anything"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Transparent Score Breakdown */}
                  <div className="pt-2 border-t border-border/50">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
                      <Info className="w-3 h-3" /> Score Breakdown
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px]">
                      <div>
                        <span className="text-muted-foreground block text-[10px]">Skill (35%)</span>
                        <span className="font-bold text-foreground">
                          {Math.round((score_breakdown.skill_match || 0) * 100)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[10px]">Proximity (25%)</span>
                        <span className="font-bold text-foreground">
                          {Math.round((score_breakdown.proximity || 0) * 100)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[10px]">Availability (20%)</span>
                        <span className="font-bold text-foreground">
                          {Math.round((score_breakdown.availability || 0) * 100)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[10px]">Trust (15%)</span>
                        <span className="font-bold text-foreground">
                          {Math.round((score_breakdown.trust || 0) * 100)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[10px]">Freshness (5%)</span>
                        <span className="font-bold text-foreground">
                          {Math.round((score_breakdown.freshness || 0) * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>

                <CardFooter className="px-5 py-3 border-t bg-muted/20 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Fixed 30-minute peer exchange</span>
                  <Button asChild size="sm" className="gap-1.5 text-xs h-8">
                    <Link href={`/swaps/${listing.id}`}>
                      <span>View & Propose Swap</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
