"use client";

import React, { useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  Filter,
  GraduationCap,
  List,
  Map as MapIcon,
  MapPin,
  Plus,
  Repeat,
  Search,
  Settings,
  Shield,
  Sparkles,
  Video,
} from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { swapApi } from "@/lib/swap-api";
import { SwapListing } from "@/types/swap";

import { SwapNav } from "@/components/swaps/swap-nav";

// Dynamically import Leaflet Map (SSR disabled)
const SwapMap = dynamic(() => import("@/components/swaps/swap-map"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[540px] rounded-2xl bg-muted/30 border border-border flex items-center justify-center text-muted-foreground text-sm">
      Loading interactive area map...
    </div>
  ),
});

export default function SwapsDiscoveryPage() {
  const [viewMode, setViewMode] = useState<"list" | "map">("list");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedMode, setSelectedMode] = useState<string>("all");
  const [selectedDistance, setSelectedDistance] = useState<string>("all");
  const [selectedSort, setSelectedSort] = useState<"newest" | "nearest" | "trust">("newest");

  const { data: profile } = useQuery({
    queryKey: ["swap-profile", "me"],
    queryFn: swapApi.getMyProfile,
  });

  const { data: taxonomy = [] } = useQuery({
    queryKey: ["swap-taxonomy"],
    queryFn: swapApi.getTaxonomy,
  });

  const { data: listingsData, isLoading } = useQuery({
    queryKey: [
      "swap-listings",
      searchQuery,
      selectedCategory,
      selectedMode,
      selectedDistance,
      selectedSort,
    ],
    queryFn: () =>
      swapApi.searchListings({
        q: searchQuery || undefined,
        category: selectedCategory !== "all" ? selectedCategory : undefined,
        mode: selectedMode !== "all" ? selectedMode : undefined,
        distance_bucket: selectedDistance !== "all" ? selectedDistance : undefined,
        sort: selectedSort,
        limit: 30,
      }),
  });

  const listings: SwapListing[] = listingsData?.items || [];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <SwapNav />

      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-r from-indigo-500/10 via-purple-500/5 to-rose-500/10 p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-semibold backdrop-blur-sm">
              <Repeat className="h-3.5 w-3.5" />
              <span>Hyper-Local Skill Swap Economy</span>
            </div>

            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
              Exchange 30 Minutes of Peer Help.{" "}
              <span className="bg-gradient-to-r from-indigo-500 to-rose-500 bg-clip-text text-transparent">
                Zero Money Involved.
              </span>
            </h1>

            <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
              Find nearby or remote peers for reciprocal 30-minute mentorship.
              Teach what you know, learn what you love.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row md:flex-col gap-2.5 shrink-0">
            <Button asChild size="lg" className="gap-2 shadow-sm font-semibold">
              <Link href="/swaps/new">
                <Plus className="w-4 h-4" />
                <span>Create Swap Offer</span>
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="gap-2">
              <Link href="/swaps/matches">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span>Matches for You</span>
              </Link>
            </Button>
            <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs text-muted-foreground">
              <Link href="/settings/swaps">
                <Settings className="w-3.5 h-3.5" />
                <span>My Profile & Preferences</span>
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Trust & Balance Bar */}
      {profile && profile.is_18_confirmed && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-2xl border border-border bg-card shadow-sm text-xs">
          <div className="space-y-1">
            <span className="text-muted-foreground uppercase font-bold text-[10px] tracking-wider">
              Trust Score
            </span>
            <div className="flex items-center gap-1.5">
              <Shield className="h-4 w-4 text-emerald-500" />
              <span className="text-lg font-bold text-foreground">{profile.trust_score}</span>
              <span className="text-muted-foreground">/ 100</span>
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-muted-foreground uppercase font-bold text-[10px] tracking-wider">
              Completed Swaps
            </span>
            <div className="flex items-center gap-1.5">
              <GraduationCap className="h-4 w-4 text-indigo-500" />
              <span className="text-lg font-bold text-foreground">{profile.completed_swaps}</span>
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-muted-foreground uppercase font-bold text-[10px] tracking-wider">
              Reciprocity Balance
            </span>
            <div className="flex items-center gap-1.5">
              <Repeat className="h-4 w-4 text-purple-500" />
              <span className="text-lg font-bold text-foreground">
                {profile.reciprocity_balance_minutes} min
              </span>
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-muted-foreground uppercase font-bold text-[10px] tracking-wider">
              My Location Area
            </span>
            <div className="flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-rose-500" />
              <span className="text-sm font-semibold truncate text-foreground">
                {profile.area_label || "Remote only"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Discovery Filters & View Controls */}
      <div className="space-y-4">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search swap offers (e.g. Python, guitar, resume, calculus)..."
              className="pl-10 h-10 rounded-xl"
            />
          </div>

          <div className="flex items-center gap-2">
            <Select
              value={selectedCategory}
              onValueChange={(val) => setSelectedCategory(val)}
            >
              <SelectTrigger className="w-[150px] h-10 rounded-xl text-xs">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {taxonomy.map((cat) => (
                  <SelectItem key={cat.category} value={cat.category}>
                    {cat.category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={selectedDistance}
              onValueChange={(val) => setSelectedDistance(val)}
            >
              <SelectTrigger className="w-[140px] h-10 rounded-xl text-xs">
                <SelectValue placeholder="Distance" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Distances</SelectItem>
                <SelectItem value="under 1 km">Under 1 km</SelectItem>
                <SelectItem value="1–3 km">1–3 km</SelectItem>
                <SelectItem value="3–5 km">3–5 km</SelectItem>
                <SelectItem value="5–10 km">5–10 km</SelectItem>
                <SelectItem value="remote">Remote / Any</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={selectedSort}
              onValueChange={(val) => setSelectedSort(val as "newest" | "nearest" | "trust")}
            >
              <SelectTrigger className="w-[130px] h-10 rounded-xl text-xs">
                <SelectValue placeholder="Sort" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="newest">Newest</SelectItem>
                <SelectItem value="nearest">Nearest</SelectItem>
                <SelectItem value="trust">Highest Trust</SelectItem>
              </SelectContent>
            </Select>

            {/* View Mode Toggle */}
            <div className="flex items-center rounded-xl border border-border p-1 bg-muted/40">
              <Button
                variant={viewMode === "list" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("list")}
                className="h-8 px-2.5 gap-1.5 text-xs rounded-lg"
              >
                <List className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">List</span>
              </Button>
              <Button
                variant={viewMode === "map" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("map")}
                className="h-8 px-2.5 gap-1.5 text-xs rounded-lg"
              >
                <MapIcon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Map</span>
              </Button>
            </div>
          </div>
        </div>

        {/* Mode Pills */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-muted-foreground text-[11px] font-medium mr-1 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Mode:
          </span>
          {[
            { id: "all", label: "All Modes" },
            { id: "video", label: "Video Only" },
            { id: "in_person", label: "In-Person Only" },
          ].map((m) => (
            <button
              key={m.id}
              onClick={() => setSelectedMode(m.id)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                selectedMode === m.id
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area: Map or Grid */}
      {viewMode === "map" ? (
        <div className="space-y-4">
          <SwapMap listings={listings} />
          <p className="text-xs text-muted-foreground text-center">
            Click on any circle to view skill swaps available in that area. Exact home coordinates are strictly hidden.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-64 rounded-2xl bg-muted/40 animate-pulse border border-border" />
              ))}
            </div>
          ) : listings.length === 0 ? (
            <div className="text-center py-16 border rounded-3xl bg-card p-8 space-y-4 shadow-sm">
              <Repeat className="w-12 h-12 text-muted-foreground mx-auto opacity-50" />
              <h3 className="text-lg font-semibold text-foreground">No swap offers found</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                No active listings match your current filters. Try relaxing the search or create the first swap offer for your area!
              </p>
              <Button asChild className="gap-2">
                <Link href="/swaps/new">
                  <Plus className="w-4 h-4" />
                  <span>Create Swap Offer</span>
                </Link>
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {listings.map((item) => (
                <Card
                  key={item.id}
                  className="rounded-2xl border-border hover:border-primary/50 transition-all hover:shadow-md flex flex-col justify-between overflow-hidden"
                >
                  <CardHeader className="p-5 pb-3 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <Link
                        href={`/profile/${item.user.username}`}
                        className="flex items-center gap-2 group"
                      >
                        <Avatar className="w-7 h-7">
                          {item.user.avatar_url && (
                            <AvatarImage src={item.user.avatar_url} />
                          )}
                          <AvatarFallback className="text-[10px]">
                            {item.user.display_name.slice(0, 2).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <span className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                          {item.user.display_name}
                        </span>
                      </Link>

                      <Badge
                        variant="outline"
                        className="text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1 border-muted-foreground/30"
                      >
                        <MapPin className="w-3 h-3 text-indigo-500" />
                        <span>{item.distance_bucket || "remote"}</span>
                      </Badge>
                    </div>

                    <h3 className="text-base font-bold text-foreground line-clamp-2 leading-snug">
                      {item.title}
                    </h3>
                  </CardHeader>

                  <CardContent className="px-5 pb-4 space-y-3">
                    <div className="space-y-1.5 text-xs">
                      <div className="flex items-start gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
                        <GraduationCap className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>Teaches: {item.skill_offered.display_name}</span>
                      </div>
                      <div className="flex items-start gap-1.5 text-indigo-600 dark:text-indigo-400 font-medium">
                        <BookOpen className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>
                          Wants: {item.skill_wanted?.display_name || "Open to anything"}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                      {item.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      {item.modes.map((mode) => (
                        <span
                          key={mode}
                          className="px-2 py-0.5 rounded-md bg-muted text-[10px] text-muted-foreground font-medium flex items-center gap-1"
                        >
                          {mode === "video" ? (
                            <Video className="w-2.5 h-2.5 text-blue-500" />
                          ) : (
                            <MapPin className="w-2.5 h-2.5 text-emerald-500" />
                          )}
                          {mode === "in_person" ? "In-Person" : "Video"}
                        </span>
                      ))}
                    </div>
                  </CardContent>

                  <CardFooter className="px-5 py-3 border-t bg-muted/20 flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground">30 min session</span>
                    <Button asChild size="sm" className="gap-1 text-xs h-8">
                      <Link href={`/swaps/${item.id}`}>
                        <span>View Details</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
