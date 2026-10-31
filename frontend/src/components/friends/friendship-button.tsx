"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clock, MessageSquare, UserCheck, UserMinus, UserPlus } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/components/ui/use-toast";
import type { FriendshipStatusResponse } from "@/types";

interface FriendshipButtonProps {
  targetUserId: string;
  targetUsername: string;
}

export function FriendshipButton({ targetUserId, targetUsername }: FriendshipButtonProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: statusData, isLoading } = useQuery<FriendshipStatusResponse>({
    queryKey: ["friends", "status", targetUserId],
    queryFn: () => apiClient.get<FriendshipStatusResponse>(`/friends/status/${targetUserId}`),
  });

  const sendMutation = useMutation({
    mutationFn: () => apiClient.post<{ message: string }>(`/friends/request/${targetUserId}`),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["friends"] });
      toast({
        title: "Friend Request",
        description: res.message || "Friend request sent!",
      });
    },
    onError: (err: Error) => {
      toast({
        title: "Failed",
        description: err.message || "Could not send friend request.",
        variant: "destructive",
      });
    },
  });

  const acceptMutation = useMutation({
    mutationFn: (requestId: string) => apiClient.post(`/friends/accept/${requestId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["friends"] });
      toast({
        title: "Connected!",
        description: `You are now friends with @${targetUsername}.`,
      });
    },
  });

  const removeMutation = useMutation({
    mutationFn: () => apiClient.delete(`/friends/${targetUserId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["friends"] });
      toast({
        title: "Removed",
        description: "Friend connection updated.",
      });
    },
  });

  if (isLoading || !statusData) {
    return (
      <Button variant="outline" size="sm" disabled className="h-9 px-3 text-xs">
        Loading...
      </Button>
    );
  }

  // Case 1: Already Friends
  if (statusData.status === "friends") {
    return (
      <div className="flex items-center gap-1.5">
        <Button
          size="sm"
          className="h-9 px-3.5 text-xs bg-primary text-primary-foreground shadow-sm flex items-center gap-1.5 font-medium"
          onClick={() => router.push(`/messages?user=${targetUserId}`)}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          <span>Message</span>
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-9 w-9 p-0 text-muted-foreground hover:text-foreground"
              title="Friend options"
            >
              <UserCheck className="h-4 w-4 text-emerald-500" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              className="text-destructive cursor-pointer flex items-center gap-2 text-xs"
              onClick={() => removeMutation.mutate()}
            >
              <UserMinus className="h-3.5 w-3.5" />
              <span>Unfriend @{targetUsername}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );
  }

  // Case 2: Outgoing Request Pending
  if (statusData.status === "pending_sent") {
    return (
      <Button
        variant="outline"
        size="sm"
        className="h-9 px-3 text-xs text-muted-foreground border-dashed flex items-center gap-1.5 hover:border-destructive hover:text-destructive transition-colors"
        onClick={() => removeMutation.mutate()}
        title="Click to cancel friend request"
      >
        <Clock className="h-3.5 w-3.5 text-amber-500" />
        <span>Request Sent</span>
      </Button>
    );
  }

  // Case 3: Incoming Request Pending
  if (statusData.status === "pending_received" && statusData.friendship_id) {
    return (
      <Button
        size="sm"
        className="h-9 px-3.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 shadow-sm font-medium"
        onClick={() => acceptMutation.mutate(statusData.friendship_id!)}
      >
        <Check className="h-3.5 w-3.5" />
        <span>Accept Request</span>
      </Button>
    );
  }

  // Case 4: No friendship yet
  return (
    <Button
      variant="outline"
      size="sm"
      className="h-9 px-3.5 text-xs flex items-center gap-1.5 hover:border-primary hover:text-primary transition-colors font-medium"
      disabled={sendMutation.isPending}
      onClick={() => sendMutation.mutate()}
    >
      <UserPlus className="h-3.5 w-3.5" />
      <span>Add Friend</span>
    </Button>
  );
}
