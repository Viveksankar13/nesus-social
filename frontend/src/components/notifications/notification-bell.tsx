"use client";

import * as React from "react";
import Link from "next/link";
import { Bell } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import type { StreamTokenResponse, UnreadCountResponse } from "@/types";

export function NotificationBell() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // 1. Unread count query (with 30s polling fallback)
  const { data: unreadData } = useQuery<UnreadCountResponse>({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => apiClient.get<UnreadCountResponse>("/notifications/unread-count"),
    enabled: !!user,
    refetchInterval: 30000, // 30s polling fallback
  });

  const unreadCount = unreadData?.unread_count ?? 0;

  // 2. Real-time Server-Sent Events connection
  React.useEffect(() => {
    if (!user) return;

    let eventSource: EventSource | null = null;
    let isSubscribed = true;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    async function connectSSE() {
      try {
        // Request single-purpose stream token
        const tokenRes = await apiClient.post<StreamTokenResponse>(
          "/notifications/token"
        );
        if (!isSubscribed || !tokenRes.token) return;

        // Connect to SSE stream
        eventSource = new EventSource(
          `/api/v1/notifications/stream?token=${encodeURIComponent(tokenRes.token)}`
        );

        eventSource.addEventListener("notification", (event) => {
          try {
            const payload = JSON.parse(event.data);
            // Invalidate notification queries to refresh lists and counters
            queryClient.invalidateQueries({
              queryKey: ["notifications", "unread-count"],
            });
            queryClient.invalidateQueries({ queryKey: ["notifications", "list"] });

            // Display live toast notification
            const notifType = payload.type || "notification";
            const title =
              notifType === "like"
                ? "New Like"
                : notifType === "comment"
                ? "New Comment"
                : notifType === "reply"
                ? "New Reply"
                : notifType === "admin_login"
                ? "Security Alert"
                : "Notification";

            toast({
              title,
              description:
                payload.payload?.message ||
                `You have a new ${notifType} on Nexus Social.`,
            });
          } catch {
            // Ignore parse errors on ping
          }
        });

        eventSource.onerror = () => {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          // Attempt reconnection after 10 seconds if still subscribed
          if (isSubscribed) {
            reconnectTimeout = setTimeout(connectSSE, 10000);
          }
        };
      } catch {
        // Token generation failed, fallback to polling
        if (isSubscribed) {
          reconnectTimeout = setTimeout(connectSSE, 15000);
        }
      }
    }

    connectSSE();

    return () => {
      isSubscribed = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [user, queryClient, toast]);

  return (
    <Link href="/notifications">
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        aria-label={`Notifications (${unreadCount} unread)`}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white shadow-sm">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </Button>
    </Link>
  );
}
