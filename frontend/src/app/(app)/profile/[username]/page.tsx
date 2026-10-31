"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  BookOpen,
  Calendar,
  Globe,
  GraduationCap,
  Heart,
  MapPin,
  MessageSquare,
  Repeat,
  Shield,
  Video,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { swapApi } from "@/lib/swap-api";
import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PostCard } from "@/components/feed/post-card";
import { EditProfileDialog } from "@/components/profile/edit-profile-dialog";
import { FriendshipButton } from "@/components/friends/friendship-button";
import { getInitials } from "@/lib/utils";
import type { FeedResponse, Post, UserProfile } from "@/types";
import type { UserSwapProfilePublic } from "@/types/swap";

export default function ProfilePage() {
  const params = useParams();
  const username = params.username as string;
  const { user: currentUser } = useAuth();

  const isOwnProfile =
    currentUser?.username.toLowerCase() === username?.toLowerCase();

  const [activeTab, setActiveTab] = React.useState<"posts" | "swaps">("posts");

  // 1. Fetch public profile
  const {
    data: profile,
    isLoading: isLoadingProfile,
    isError: isProfileError,
  } = useQuery<UserProfile>({
    queryKey: ["users", "profile", username],
    queryFn: () => apiClient.get<UserProfile>(`/users/${username}`),
    enabled: !!username,
  });

  // 2. Fetch public swap profile
  const { data: swapProfile } = useQuery<UserSwapProfilePublic>({
    queryKey: ["swap-profile", username],
    queryFn: () => swapApi.getPublicProfile(username),
    enabled: !!username,
    retry: false,
  });

  // 3. Fetch user's authored posts
  const { data: postsData, isLoading: isLoadingPosts } = useQuery<FeedResponse>({
    queryKey: ["posts", "user", username],
    queryFn: () => {
      // If own profile, query with feed_type=mine
      const queryParam = isOwnProfile ? "feed_type=mine" : "feed_type=all";
      return apiClient.get<FeedResponse>(`/posts?${queryParam}&limit=20`);
    },
    enabled: !!profile,
  });

  // Filter posts authored by this user if viewing someone else
  const posts = React.useMemo(() => {
    if (!postsData?.items) return [];
    if (isOwnProfile) return postsData.items;
    return postsData.items.filter(
      (p: Post) => p.author.username.toLowerCase() === username?.toLowerCase()
    );
  }, [postsData, isOwnProfile, username]);

  if (isLoadingProfile) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <Skeleton className="h-44 w-full rounded-2xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
      </div>
    );
  }

  if (isProfileError || !profile) {
    return (
      <div className="max-w-2xl mx-auto rounded-2xl border border-destructive/20 bg-destructive/10 p-8 text-center">
        <p className="text-base text-destructive font-semibold">User not found</p>
        <p className="text-xs text-muted-foreground mt-1">
          @{username} does not exist or has deactivated their account.
        </p>
        <Link href="/feed" className="inline-block mt-4">
          <Button variant="outline" size="sm">
            Back to Feed
          </Button>
        </Link>
      </div>
    );
  }

  const joinDate = new Date(profile.created_at).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Profile Header Card */}
      <Card className="border shadow-sm overflow-hidden rounded-2xl">
        <div className="h-24 bg-gradient-to-r from-primary/30 via-indigo-500/20 to-purple-500/30" />
        <CardContent className="p-6 pt-0 relative">
          <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between -mt-12 sm:-mt-14 mb-4 gap-3">
            <Avatar className="h-24 w-24 sm:h-28 sm:w-28 border-4 border-background shadow-md">
              {profile.avatar_url && (
                <AvatarImage src={profile.avatar_url} alt={profile.display_name} />
              )}
              <AvatarFallback className="text-2xl font-bold">
                {getInitials(profile.display_name)}
              </AvatarFallback>
            </Avatar>

            {isOwnProfile && currentUser && (
              <EditProfileDialog user={currentUser} />
            )}
            {!isOwnProfile && currentUser && (
              <FriendshipButton targetUserId={profile.id} targetUsername={profile.username} />
            )}
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl sm:text-2xl font-bold text-foreground">
                  {profile.display_name}
                </h1>
                {profile.role === "admin" && (
                  <Badge variant="default" className="text-[10px] h-5 px-1.5 uppercase font-bold">
                    <Shield className="h-3 w-3 mr-1" />
                    Admin
                  </Badge>
                )}
                {profile.usn && (
                  <Badge variant="outline" className="text-[11px] h-5 px-2 font-mono font-semibold border-indigo-500/30 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                    USN: {profile.usn}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">@{profile.username}</p>
            </div>

            {profile.bio && (
              <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                {profile.bio}
              </p>
            )}

            {/* Metadata tags */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
              {profile.location && (
                <div className="flex items-center space-x-1">
                  <MapPin className="h-3.5 w-3.5 text-muted-foreground/70" />
                  <span>{profile.location}</span>
                </div>
              )}

              {profile.website && (
                <div className="flex items-center space-x-1">
                  <Globe className="h-3.5 w-3.5 text-muted-foreground/70" />
                  <a
                    href={
                      profile.website.startsWith("http")
                        ? profile.website
                        : `https://${profile.website}`
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline truncate max-w-[180px]"
                  >
                    {profile.website.replace(/^https?:\/\//, "")}
                  </a>
                </div>
              )}

              <div className="flex items-center space-x-1">
                <Calendar className="h-3.5 w-3.5 text-muted-foreground/70" />
                <span>Joined {joinDate}</span>
              </div>
            </div>

            {/* Stats Counters */}
            <div className="flex items-center space-x-6 border-t pt-4 text-sm">
              <div className="flex items-center space-x-1.5">
                <MessageSquare className="h-4 w-4 text-primary" />
                <span className="font-bold text-foreground">
                  {profile.posts_count}
                </span>
                <span className="text-muted-foreground">Posts</span>
              </div>

              <div className="flex items-center space-x-1.5">
                <Heart className="h-4 w-4 text-rose-500" />
                <span className="font-bold text-foreground">
                  {profile.likes_received_count}
                </span>
                <span className="text-muted-foreground">Likes Received</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Profile Section Tabs */}
      <div className="flex border-b space-x-1">
        <button
          type="button"
          onClick={() => setActiveTab("posts")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "posts"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <MessageSquare className="h-4 w-4" />
          <span>Posts ({profile.posts_count})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("swaps")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "swaps"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Repeat className="h-4 w-4" />
          <span>Skills & Swaps</span>
          {swapProfile && swapProfile.teach_skills.length > 0 && (
            <Badge variant="secondary" className="text-[10px] h-4 px-1.5 ml-1">
              {swapProfile.teach_skills.length}
            </Badge>
          )}
        </button>
      </div>

      {/* Tab Content: Posts */}
      {activeTab === "posts" && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
            Posts by {profile.display_name}
          </h2>

          {isLoadingPosts && (
            <div className="space-y-4">
              {[1, 2].map((i) => (
                <Skeleton key={i} className="h-32 w-full rounded-xl" />
              ))}
            </div>
          )}

          {!isLoadingPosts && posts.length > 0 && (
            <div className="space-y-4">
              {posts.map((post: Post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          )}

          {!isLoadingPosts && posts.length === 0 && (
            <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground text-sm">
              No posts published yet.
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Skills & Swaps */}
      {activeTab === "swaps" && (
        <div className="space-y-6">
          {!swapProfile ? (
            <div className="rounded-2xl border border-dashed p-8 text-center space-y-3">
              <Repeat className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="text-sm text-muted-foreground">
                {isOwnProfile
                  ? "You haven't configured your Skill Swap profile yet."
                  : "This user hasn't set up their Skill Swap profile yet."}
              </p>
              {isOwnProfile && (
                <Button asChild size="sm">
                  <Link href="/swaps/onboarding">Start Onboarding Wizard</Link>
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {/* Trust Score & Match Header */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-5 rounded-2xl border bg-card shadow-xs">
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">
                    Trust Score
                  </span>
                  <div className="flex items-center gap-1.5">
                    <Shield className="h-4 w-4 text-primary" />
                    <span className="text-xl font-bold">{swapProfile.trust_score}</span>
                    <span className="text-xs text-muted-foreground">/ 100</span>
                  </div>
                  {swapProfile.badges.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {swapProfile.badges.map((b) => (
                        <Badge
                          key={b}
                          variant="outline"
                          className="text-[10px] bg-primary/5 text-primary border-primary/20"
                        >
                          {b}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">
                    Distance & Area
                  </span>
                  <div className="flex items-center gap-1.5">
                    <MapPin className="h-4 w-4 text-rose-500 shrink-0" />
                    <span className="text-sm font-semibold capitalize">
                      {swapProfile.distance_bucket}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground truncate">
                    {swapProfile.area_label || "Remote Only"}
                  </p>
                </div>

                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">
                    Exchange Modes
                  </span>
                  <div className="flex items-center gap-2 pt-0.5">
                    {swapProfile.modes.includes("video") && (
                      <Badge variant="secondary" className="text-[10px] gap-1">
                        <Video className="h-3 w-3" /> Video
                      </Badge>
                    )}
                    {swapProfile.modes.includes("in_person") && (
                      <Badge variant="secondary" className="text-[10px] gap-1">
                        <MapPin className="h-3 w-3" /> In-Person
                      </Badge>
                    )}
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    {swapProfile.completed_swaps} completed swaps
                  </p>
                </div>
              </div>

              {/* Skills I Can Teach */}
              <div className="space-y-3 p-5 rounded-2xl border bg-card">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold flex items-center gap-2">
                    <GraduationCap className="h-4 w-4 text-primary" />
                    <span>Skills I Can Teach ({swapProfile.teach_skills.length})</span>
                  </h3>
                </div>

                {swapProfile.teach_skills.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    No teaching skills declared.
                  </p>
                ) : (
                  <div className="grid gap-2.5">
                    {swapProfile.teach_skills.map((ts) => (
                      <div
                        key={ts.id || ts.skill_slug}
                        className="p-3 rounded-xl border bg-accent/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm">
                              {ts.skill?.display_name || ts.skill_slug.replace(/-/g, " ")}
                            </span>
                            <Badge variant="outline" className="text-[10px] capitalize">
                              {ts.level}
                            </Badge>
                            {ts.years_experience ? (
                              <span className="text-[11px] text-muted-foreground">
                                {ts.years_experience} yrs exp
                              </span>
                            ) : null}
                          </div>
                          {ts.notes && (
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                              {ts.notes}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Skills I Want to Learn */}
              <div className="space-y-3 p-5 rounded-2xl border bg-card">
                <h3 className="text-sm font-bold flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-primary" />
                  <span>Skills I Want to Learn ({swapProfile.learn_skills.length})</span>
                </h3>

                {swapProfile.learn_skills.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    No learning goals declared.
                  </p>
                ) : (
                  <div className="grid gap-2.5">
                    {swapProfile.learn_skills.map((ls) => (
                      <div
                        key={ls.id || ls.skill_slug}
                        className="p-3 rounded-xl border bg-accent/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm">
                              {ls.skill?.display_name || ls.skill_slug.replace(/-/g, " ")}
                            </span>
                            <Badge variant="outline" className="text-[10px] capitalize">
                              {ls.level}
                            </Badge>
                          </div>
                          {ls.notes && (
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                              {ls.notes}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2 pt-2">
                {isOwnProfile ? (
                  <Button asChild size="sm" variant="outline" className="gap-1.5">
                    <Link href="/settings/swaps">
                      <Repeat className="h-4 w-4" />
                      <span>Edit Swap Preferences</span>
                    </Link>
                  </Button>
                ) : (
                  <Button asChild size="sm" className="gap-1.5 shadow-sm">
                    <Link href={`/swaps/new?partner=${profile.username}`}>
                      <Repeat className="h-4 w-4" />
                      <span>Propose a 30-Min Swap</span>
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
