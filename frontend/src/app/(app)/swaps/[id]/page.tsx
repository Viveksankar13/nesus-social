"use client";

import React from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpen,
  Clock,
  GraduationCap,
  HeartHandshake,
  Loader2,
  MapPin,
  PauseCircle,
  PlayCircle,
  Repeat,
  Share2,
  Shield,
  ShieldCheck,
  Video,
} from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { swapApi } from "@/lib/swap-api";

export default function SwapListingDetailPage() {
  const params = useParams();
  const listingId = params?.id as string;
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: listing, isLoading, error } = useQuery({
    queryKey: ["swap-listing", listingId],
    queryFn: () => swapApi.getListingById(listingId),
    enabled: !!listingId,
  });

  const isOwner = user?.id === listing?.user_id;

  // Share to Feed Mutation
  const shareMutation = useMutation({
    mutationFn: () => swapApi.shareListingToFeed(listingId),
    onSuccess: () => {
      toast({
        title: "Shared to Social Feed!",
        description: "Your swap offer is now visible to friends and followers.",
      });
      queryClient.invalidateQueries({ queryKey: ["posts"] });
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      toast({
        title: "Share failed",
        description: err.response?.data?.detail || "Could not share listing to feed.",
        variant: "destructive",
      });
    },
  });

  // Toggle Status Mutation (Pause / Activate)
  const toggleStatusMutation = useMutation({
    mutationFn: (newStatus: "active" | "paused") =>
      swapApi.updateListing(listingId, { status: newStatus }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["swap-listing", listingId] });
      toast({
        title: `Offer ${data.status === "active" ? "Activated" : "Paused"}`,
        description: `Your swap offer is now ${data.status}.`,
      });
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      toast({
        title: "Update failed",
        description: err.response?.data?.detail || "Could not update status.",
        variant: "destructive",
      });
    },
  });

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground">Loading swap offer details...</span>
      </div>
    );
  }

  if (error || !listing) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center space-y-4">
        <Repeat className="w-12 h-12 text-muted-foreground mx-auto opacity-50" />
        <h2 className="text-xl font-bold text-foreground">Swap offer not found</h2>
        <p className="text-sm text-muted-foreground">
          This listing may have been removed, closed, or set to private.
        </p>
        <Button asChild>
          <Link href="/swaps">Back to Swaps Discovery</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/swaps"
          className="hover:text-foreground text-xs text-muted-foreground flex items-center gap-1 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Swaps Discovery</span>
        </Link>

        {isOwner && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                toggleStatusMutation.mutate(
                  listing.status === "active" ? "paused" : "active"
                )
              }
              disabled={toggleStatusMutation.isPending}
              className="gap-1.5 text-xs h-8"
            >
              {listing.status === "active" ? (
                <>
                  <PauseCircle className="w-3.5 h-3.5" />
                  <span>Pause Offer</span>
                </>
              ) : (
                <>
                  <PlayCircle className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Reactivate</span>
                </>
              )}
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => shareMutation.mutate()}
              disabled={shareMutation.isPending || listing.status !== "active"}
              className="gap-1.5 text-xs h-8"
            >
              <Share2 className="w-3.5 h-3.5 text-indigo-500" />
              <span>Share to Feed</span>
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Details (2 cols) */}
        <div className="md:col-span-2 space-y-5">
          <Card className="rounded-2xl border-border shadow-sm">
            <CardHeader className="p-6 pb-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant={listing.status === "active" ? "default" : "secondary"}
                  className="capitalize text-[11px]"
                >
                  {listing.status}
                </Badge>
                <Badge
                  variant="outline"
                  className="text-[11px] gap-1 border-muted-foreground/30"
                >
                  <Clock className="w-3 h-3 text-indigo-500" />
                  <span>Fixed 30-minute peer swap</span>
                </Badge>
                <Badge
                  variant="outline"
                  className="text-[11px] gap-1 border-muted-foreground/30"
                >
                  <MapPin className="w-3 h-3 text-rose-500" />
                  <span>{listing.distance_bucket || "remote"}</span>
                </Badge>
              </div>

              <h1 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight leading-snug">
                {listing.title}
              </h1>
            </CardHeader>

            <CardContent className="px-6 pb-6 space-y-6">
              {/* Skills Exchange Matrix */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 rounded-xl border border-border bg-muted/20">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                    <GraduationCap className="w-3.5 h-3.5 text-emerald-500" />
                    Offered to Teach
                  </span>
                  <div className="font-semibold text-foreground text-sm">
                    {listing.skill_offered.display_name}
                  </div>
                  <span className="text-[11px] text-muted-foreground">
                    Category: {listing.skill_offered.category}
                  </span>
                </div>

                <div className="space-y-1 sm:border-l sm:border-border sm:pl-3">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                    <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                    Wants to Learn
                  </span>
                  <div className="font-semibold text-foreground text-sm">
                    {listing.skill_wanted?.display_name || "✨ Open to anything / Pay it forward"}
                  </div>
                  <span className="text-[11px] text-muted-foreground">
                    {listing.skill_wanted ? `Category: ${listing.skill_wanted.category}` : "Reciprocal peer grace"}
                  </span>
                </div>
              </div>

              {/* Description */}
              <div className="space-y-2">
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                  Offer Description
                </h3>
                <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
                  {listing.description}
                </p>
              </div>

              {/* Modes & Area */}
              <div className="flex flex-wrap items-center gap-4 text-xs pt-2 border-t border-border/50">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <span className="font-semibold">Modes:</span>
                  {listing.modes.map((m) => (
                    <span
                      key={m}
                      className="px-2 py-0.5 rounded-md bg-muted text-foreground font-medium flex items-center gap-1"
                    >
                      {m === "video" ? <Video className="w-3 h-3 text-blue-500" /> : <MapPin className="w-3 h-3 text-emerald-500" />}
                      {m === "in_person" ? "In-Person" : "Video"}
                    </span>
                  ))}
                </div>

                {listing.area_label && (
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <span className="font-semibold">Area:</span>
                    <span className="text-foreground font-medium">{listing.area_label}</span>
                  </div>
                )}
              </div>

              {/* Tags */}
              {listing.tags && listing.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {listing.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs px-2 py-0.5">
                      #{tag}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar Info & Action (1 col) */}
        <div className="space-y-5">
          <Card className="rounded-2xl border-border shadow-sm p-5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Swap Partner
            </h3>

            <Link
              href={`/profile/${listing.user.username}`}
              className="flex items-center gap-3 group"
            >
              <Avatar className="w-12 h-12">
                {listing.user.avatar_url && <AvatarImage src={listing.user.avatar_url} />}
                <AvatarFallback>
                  {listing.user.display_name.slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="space-y-0.5">
                <div className="font-bold text-sm text-foreground group-hover:text-primary transition-colors">
                  {listing.user.display_name}
                </div>
                <div className="text-xs text-muted-foreground">@{listing.user.username}</div>
                {listing.user.usn && (
                  <div className="text-[10px] text-muted-foreground">USN: {listing.user.usn}</div>
                )}
              </div>
            </Link>

            <div className="p-3 rounded-xl bg-muted/40 border border-border text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-1">
                  <Shield className="w-3.5 h-3.5 text-emerald-500" /> Trust Score
                </span>
                <span className="font-bold text-foreground">100 / 100</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-1">
                  <HeartHandshake className="w-3.5 h-3.5 text-indigo-500" /> Completed
                </span>
                <span className="font-bold text-foreground">Verified peer</span>
              </div>
            </div>

            {/* Action CTA */}
            {!isOwner ? (
              <div className="pt-2 space-y-2">
                <Button className="w-full gap-2 font-semibold shadow-sm" size="lg">
                  <Repeat className="w-4 h-4" />
                  <span>Propose a 30-Min Swap</span>
                </Button>
                <p className="text-[11px] text-muted-foreground text-center">
                  Propose up to 3 preferred 30-minute time slots. No money involved.
                </p>
              </div>
            ) : (
              <div className="pt-2 text-center text-xs text-muted-foreground">
                This is your active listing. You can share it to the main feed or pause it at any time.
              </div>
            )}
          </Card>

          {/* Safety & Non-monetary guarantee banner */}
          <div className="p-4 rounded-2xl border border-indigo-500/20 bg-indigo-500/5 text-xs space-y-2">
            <div className="flex items-center gap-1.5 font-semibold text-foreground">
              <ShieldCheck className="w-4 h-4 text-indigo-500" />
              <span>Peer Safety Guidance</span>
            </div>
            <p className="text-muted-foreground leading-relaxed text-[11px]">
              • Swaps are strictly peer exchanges with zero money or fees.<br />
              • For in-person sessions, meet only in public university or tech spaces.<br />
              • Double-blind reviews unlock after both complete their 30-minute half.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
