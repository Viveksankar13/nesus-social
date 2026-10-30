"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  CheckCheck,
  Heart,
  Loader2,
  Lock,
  MessageCircle,
  Reply,
  ShieldAlert,
} from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { cn, timeAgo } from "@/lib/utils";
import type { Notification, NotificationListResponse } from "@/types";

export default function NotificationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [unreadOnly, setUnreadOnly] = React.useState(false);

  // 1. Notifications Infinite Query
  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
  } = useInfiniteQuery<NotificationListResponse>({
    queryKey: ["notifications", "list", { unreadOnly }],
    queryFn: ({ pageParam }) => {
      const params: Record<string, string | number | boolean> = {
        limit: 20,
        unread_only: unreadOnly,
      };
      if (pageParam) {
        params.cursor = pageParam as string;
      }
      return apiClient.get<NotificationListResponse>("/notifications", params);
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.next_cursor ?? undefined : undefined,
  });

  // Total unread count from the first page
  const unreadCount = data?.pages[0]?.unread_count ?? 0;

  // 2. Mark single notification as read mutation
  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) =>
      apiClient.patch(`/notifications/${notificationId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  // 3. Mark all as read mutation
  const markAllReadMutation = useMutation({
    mutationFn: () => apiClient.patch("/notifications/read-all"),
    onSuccess: () => {
      toast({
        title: "All marked as read",
        description: "All unread notifications have been marked as read.",
      });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: () => {
      toast({
        variant: "destructive",
        title: "Failed",
        description: "Unable to mark all notifications as read.",
      });
    },
  });

  // Flattened notifications
  const notifications = React.useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data]
  );

  const handleNotificationClick = async (notif: Notification) => {
    if (!notif.is_read) {
      markReadMutation.mutate(notif.id);
    }
    const postId = notif.payload?.post_id as string | undefined;
    if (postId) {
      router.push(`/posts/${postId}`);
    }
  };

  const renderIcon = (type: Notification["type"]) => {
    switch (type) {
      case "like":
        return <Heart className="h-5 w-5 text-rose-500 fill-rose-500/20" />;
      case "comment":
        return <MessageCircle className="h-5 w-5 text-blue-500 fill-blue-500/20" />;
      case "reply":
        return <Reply className="h-5 w-5 text-indigo-500" />;
      case "moderation":
      case "flagged":
        return <ShieldAlert className="h-5 w-5 text-amber-500" />;
      case "admin_login":
        return <Lock className="h-5 w-5 text-purple-500" />;
      default:
        return <Bell className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const renderContent = (notif: Notification) => {
    const payload = notif.payload || {};
    switch (notif.type) {
      case "like": {
        const liker = (payload.liker_name || payload.liker_username || "Someone") as string;
        return (
          <p className="text-sm">
            <span className="font-semibold text-foreground">{liker}</span> liked your post.
          </p>
        );
      }
      case "comment": {
        const commenter = (payload.author_name || payload.author_username || "Someone") as string;
        return (
          <p className="text-sm">
            <span className="font-semibold text-foreground">{commenter}</span> commented on your post.
          </p>
        );
      }
      case "reply": {
        const replier = (payload.author_name || payload.author_username || "Someone") as string;
        return (
          <p className="text-sm">
            <span className="font-semibold text-foreground">{replier}</span> replied to your comment.
          </p>
        );
      }
      case "moderation":
      case "flagged": {
        const msg = (payload.message || "A post or comment has triggered moderation review.") as string;
        return (
          <p className="text-sm">
            <span className="font-semibold text-amber-500">Moderation Alert:</span> {msg}
          </p>
        );
      }
      case "admin_login": {
        const ip = (payload.ip || "unknown IP") as string;
        return (
          <p className="text-sm">
            <span className="font-semibold text-purple-500">Security Alert:</span> Admin login detected from {ip}.
          </p>
        );
      }
      default: {
        const msg = (payload.message || "You have a new notification.") as string;
        return <p className="text-sm">{msg}</p>;
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
          <p className="text-sm text-muted-foreground">
            Stay updated on likes, comments, replies, and system alerts
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending}
            >
              {markAllReadMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CheckCheck className="mr-2 h-4 w-4 text-primary" />
              )}
              Mark all as read
            </Button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-border pb-3">
        <Button
          variant={!unreadOnly ? "default" : "ghost"}
          size="sm"
          onClick={() => setUnreadOnly(false)}
        >
          All
        </Button>
        <Button
          variant={unreadOnly ? "default" : "ghost"}
          size="sm"
          onClick={() => setUnreadOnly(true)}
        >
          Unread
          {unreadCount > 0 && (
            <span className="ml-1.5 rounded-full bg-rose-500/20 px-1.5 py-0.5 text-xs font-semibold text-rose-500">
              {unreadCount}
            </span>
          )}
        </Button>
      </div>

      {/* Notifications List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="flex items-center gap-4 p-4">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/4" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : isError ? (
        <Card className="p-8 text-center">
          <p className="text-destructive mb-3">Failed to load notifications.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Try again
          </Button>
        </Card>
      ) : notifications.length === 0 ? (
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <div className="mb-4 rounded-full bg-muted p-4">
            <Bell className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="font-semibold text-foreground">No notifications yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {unreadOnly
              ? "You have no unread notifications right now."
              : "When someone likes or comments on your posts, you'll see them here."}
          </p>
        </Card>
      ) : (
        <div className="space-y-2">
          {notifications.map((notif) => {
            const hasLink = Boolean(notif.payload?.post_id);
            return (
              <div
                key={notif.id}
                onClick={() => handleNotificationClick(notif)}
                className={cn(
                  "group flex items-start gap-3.5 rounded-lg border p-4 transition-colors",
                  hasLink ? "cursor-pointer hover:bg-accent/50" : "cursor-default",
                  notif.is_read
                    ? "border-border/60 bg-card text-muted-foreground"
                    : "border-primary/20 bg-primary/5 text-foreground shadow-sm"
                )}
              >
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-background shadow-xs">
                  {renderIcon(notif.type)}
                </div>

                <div className="flex-1 space-y-1">
                  <div className="flex items-start justify-between gap-2">
                    {renderContent(notif)}
                    {!notif.is_read && (
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {timeAgo(notif.created_at)}
                  </p>
                </div>
              </div>
            );
          })}

          {hasNextPage && (
            <div className="pt-4 text-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading more...
                  </>
                ) : (
                  "Load more notifications"
                )}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
