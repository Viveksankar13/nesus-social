"use client";

import * as React from "react";
import { Loader2, MessageSquarePlus } from "lucide-react";
import { useInfiniteQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PostComposer } from "@/components/feed/post-composer";
import { PostCard } from "@/components/feed/post-card";
import type { FeedResponse, Post } from "@/types";

export default function FeedPage() {
  const [feedType, setFeedType] = React.useState<"all" | "mine">("all");

  const {
    data,
    isLoading,
    isError,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
  } = useInfiniteQuery<FeedResponse, Error>({
    queryKey: ["posts", "feed", feedType],
    queryFn: async ({ pageParam }) => {
      const cursorQuery = pageParam ? `&cursor=${encodeURIComponent(pageParam as string)}` : "";
      return apiClient.get<FeedResponse>(
        `/posts?feed_type=${feedType}&limit=10${cursorQuery}`
      );
    },
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.next_cursor : undefined),
  });

  const posts = React.useMemo(() => {
    return data?.pages.flatMap((page) => page.items) ?? [];
  }, [data]);

  return (
    <div className="max-w-2xl mx-auto">
      {/* Feed type tabs */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold tracking-tight text-foreground">Community Feed</h1>
        <Tabs
          value={feedType}
          onValueChange={(val) => setFeedType(val as "all" | "mine")}
        >
          <TabsList className="grid grid-cols-2 w-48">
            <TabsTrigger value="all" className="text-xs">
              All Posts
            </TabsTrigger>
            <TabsTrigger value="mine" className="text-xs">
              My Posts
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Post Composer */}
      <PostComposer />

      {/* Loading state skeleton */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="border rounded-xl p-5 space-y-3 bg-card">
              <div className="flex items-center space-x-3">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="space-y-1.5 flex-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-20" />
                </div>
              </div>
              <Skeleton className="h-16 w-full" />
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-6 text-center">
          <p className="text-sm text-destructive font-medium">
            {error?.message || "Could not load posts feed."}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="mt-3 text-xs"
          >
            Try Again
          </Button>
        </div>
      )}

      {/* Feed Posts List */}
      {!isLoading && posts.length > 0 && (
        <div className="space-y-4">
          {posts.map((post: Post) => (
            <PostCard key={post.id} post={post} />
          ))}

          {/* Load more button */}
          {hasNextPage && (
            <div className="pt-2 pb-6 text-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="text-xs w-full sm:w-auto"
              >
                {isFetchingNextPage ? (
                  <>
                    <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                    Loading older posts...
                  </>
                ) : (
                  "Load More Posts"
                )}
              </Button>
            </div>
          )}

          {!hasNextPage && posts.length > 5 && (
            <p className="text-center text-xs text-muted-foreground py-6">
              You&apos;ve reached the end of the feed.
            </p>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && posts.length === 0 && !isError && (
        <div className="rounded-2xl border border-dashed p-12 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground mb-3">
            <MessageSquarePlus className="h-6 w-6" />
          </div>
          <h3 className="text-base font-semibold text-foreground">No posts yet</h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
            {feedType === "mine"
              ? "You haven't authored any posts yet. Create your first post using the composer above!"
              : "The community feed is quiet. Share the first update with your thoughts!"}
          </p>
        </div>
      )}
    </div>
  );
}
