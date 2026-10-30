"use client";

import * as React from "react";
import { Loader2, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import type { SmartRepliesResponse } from "@/types";

interface SmartRepliesBarProps {
  postId: string;
  commentId?: string;
  onSelectReply: (reply: string) => void;
}

export function SmartRepliesBar({
  postId,
  commentId,
  onSelectReply,
}: SmartRepliesBarProps) {
  const { data, isLoading } = useQuery<SmartRepliesResponse>({
    queryKey: ["ai", "smart-replies", postId, commentId || "root"],
    queryFn: () =>
      apiClient.post<SmartRepliesResponse>("/ai/smart-replies", {
        post_id: postId,
        comment_id: commentId || null,
      }),
    staleTime: 5 * 60 * 1000, // 5 min cache
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center space-x-2 py-1 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin text-primary" />
        <span>Loading smart suggestions...</span>
      </div>
    );
  }

  if (!data?.replies || data.replies.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5 py-1.5">
      <div className="flex items-center space-x-1 text-[11px] font-semibold text-primary mr-1">
        <Sparkles className="h-3 w-3" />
        <span className="hidden sm:inline">Suggestions:</span>
      </div>
      {data.replies.map((reply, idx) => (
        <button
          key={idx}
          type="button"
          onClick={() => onSelectReply(reply)}
          className="rounded-full border border-primary/20 bg-background/80 px-2.5 py-1 text-xs text-foreground transition-all hover:bg-primary/10 hover:border-primary/40 active:scale-95 text-left"
        >
          {reply}
        </button>
      ))}
    </div>
  );
}
