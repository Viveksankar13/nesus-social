"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CornerDownRight, Loader2, MessageCircle, Send, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { PostCard } from "@/components/feed/post-card";
import { AISummaryCard } from "@/components/ai/ai-summary-card";
import { SmartRepliesBar } from "@/components/ai/smart-replies-bar";
import { getInitials, timeAgo } from "@/lib/utils";
import type { Comment, Post } from "@/types";

export default function PostDetailPage() {
  const params = useParams();
  const postId = params.id as string;
  const { user, isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [commentText, setCommentText] = React.useState("");
  const [replyingToId, setReplyingToId] = React.useState<string | null>(null);
  const [replyText, setReplyText] = React.useState("");

  // 1. Fetch Post Query
  const {
    data: post,
    isLoading: isLoadingPost,
    isError: isPostError,
  } = useQuery<Post>({
    queryKey: ["posts", postId],
    queryFn: () => apiClient.get<Post>(`/posts/${postId}`),
    enabled: !!postId,
  });

  // 2. Fetch Threaded Comments Query
  const {
    data: comments,
    isLoading: isLoadingComments,
  } = useQuery<Comment[]>({
    queryKey: ["posts", postId, "comments"],
    queryFn: () => apiClient.get<Comment[]>(`/posts/${postId}/comments`),
    enabled: !!postId,
  });

  // 3. Add Comment Mutation
  const addCommentMutation = useMutation({
    mutationFn: (data: { content: string; parent_id?: string | null }) =>
      apiClient.post<Comment>(`/posts/${postId}/comments`, data),
    onSuccess: () => {
      setCommentText("");
      setReplyingToId(null);
      setReplyText("");
      queryClient.invalidateQueries({ queryKey: ["posts", postId, "comments"] });
      queryClient.invalidateQueries({ queryKey: ["posts", postId] });
      queryClient.invalidateQueries({ queryKey: ["posts", "feed"] });
      toast({ title: "Comment added!" });
    },
    onError: (err: Error) => {
      toast({
        title: "Could not add comment",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  // 4. Delete Comment Mutation
  const deleteCommentMutation = useMutation({
    mutationFn: (commentId: string) => apiClient.delete(`/comments/${commentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts", postId, "comments"] });
      queryClient.invalidateQueries({ queryKey: ["posts", postId] });
      queryClient.invalidateQueries({ queryKey: ["posts", "feed"] });
      toast({ title: "Comment deleted" });
    },
    onError: (err: Error) => {
      toast({
        title: "Failed to delete comment",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  const handleRootCommentSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = commentText.trim();
    if (!text || text.length > 500) return;
    addCommentMutation.mutate({ content: text, parent_id: null });
  };

  const handleReplySubmit = (parentId: string) => {
    const text = replyText.trim();
    if (!text || text.length > 500) return;
    addCommentMutation.mutate({ content: text, parent_id: parentId });
  };

  if (isLoadingPost) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <Skeleton className="h-6 w-24 mb-4" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }

  if (isPostError || !post) {
    return (
      <div className="max-w-2xl mx-auto rounded-xl border border-destructive/20 bg-destructive/10 p-8 text-center">
        <p className="text-base text-destructive font-semibold">Post not found</p>
        <p className="text-xs text-muted-foreground mt-1">
          This post may have been removed or does not exist.
        </p>
        <Link href="/feed" className="inline-block mt-4">
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Feed
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back button */}
      <div className="mb-4">
        <Link
          href="/feed"
          className="inline-flex items-center text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
          Back to Feed
        </Link>
      </div>

      {/* Main Post Card */}
      <PostCard post={post} showCommentsLink={false} />

      {/* AI Discussion Summary Card (Shown if >= 3 comments) */}
      <AISummaryCard postId={post.id} commentsCount={post.comments_count} />

      {/* Comment Composer */}
      <Card className="border shadow-sm mb-6">
        <CardContent className="p-4 space-y-2">
          <form onSubmit={handleRootCommentSubmit} className="space-y-3">
            <div className="flex items-start space-x-3">
              <Avatar className="h-8 w-8 mt-1 shrink-0">
                {user?.avatar_url && (
                  <AvatarImage src={user.avatar_url} alt={user.display_name} />
                )}
                <AvatarFallback>
                  {getInitials(user?.display_name || "User")}
                </AvatarFallback>
              </Avatar>

              <div className="flex-1 space-y-2">
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Share your perspective or reply..."
                  rows={2}
                  maxLength={500}
                  className="w-full resize-none bg-transparent p-1 text-sm outline-none placeholder:text-muted-foreground focus:ring-0"
                />

                {/* Smart Replies Suggestions */}
                <SmartRepliesBar
                  postId={post.id}
                  onSelectReply={(text) => setCommentText(text)}
                />
              </div>
            </div>

            <div className="flex items-center justify-between border-t pt-2.5">
              <span className="text-[11px] text-muted-foreground">
                {500 - commentText.length} characters left
              </span>

              <Button
                type="submit"
                size="sm"
                disabled={!commentText.trim() || addCommentMutation.isPending}
                className="h-8 text-xs"
              >
                {addCommentMutation.isPending ? (
                  <>
                    <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                    Posting...
                  </>
                ) : (
                  <>
                    <Send className="mr-1.5 h-3 w-3" />
                    Reply
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Comments Section */}
      <div className="space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center space-x-2">
          <MessageCircle className="h-4 w-4" />
          <span>Comments ({comments?.length ?? 0})</span>
        </h2>

        {isLoadingComments && (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="border rounded-xl p-4 space-y-2 bg-card">
                <div className="flex items-center space-x-2">
                  <Skeleton className="h-7 w-7 rounded-full" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-10 w-full" />
              </div>
            ))}
          </div>
        )}

        {/* Threaded Comments List */}
        {!isLoadingComments && comments && comments.length > 0 && (
          <div className="space-y-3">
            {comments.map((comment) => {
              const canDeleteComment =
                user?.id === comment.author_id || isAdmin;

              return (
                <div
                  key={comment.id}
                  className="rounded-xl border bg-card p-4 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-2.5">
                      <Avatar className="h-7 w-7">
                        {comment.author?.avatar_url && (
                          <AvatarImage
                            src={comment.author.avatar_url}
                            alt={comment.author.display_name}
                          />
                        )}
                        <AvatarFallback>
                          {getInitials(comment.author?.display_name || "User")}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="flex items-center space-x-1.5">
                          <span className="text-xs font-semibold text-foreground">
                            {comment.author?.display_name || "Deleted User"}
                          </span>
                          <span className="text-[11px] text-muted-foreground">
                            @{comment.author?.username}
                          </span>
                        </div>
                        <span className="text-[10px] text-muted-foreground">
                          {timeAgo(comment.created_at)}
                        </span>
                      </div>
                    </div>

                    {canDeleteComment && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-muted-foreground hover:text-destructive"
                        onClick={() => deleteCommentMutation.mutate(comment.id)}
                        title="Delete comment"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>

                  <p className="text-xs sm:text-sm text-foreground whitespace-pre-wrap pl-9">
                    {comment.content}
                  </p>

                  {/* Reply button */}
                  <div className="pl-9 flex items-center space-x-4">
                    <button
                      onClick={() =>
                        setReplyingToId(
                          replyingToId === comment.id ? null : comment.id
                        )
                      }
                      className="text-xs font-medium text-primary hover:underline flex items-center space-x-1"
                    >
                      <CornerDownRight className="h-3 w-3" />
                      <span>{replyingToId === comment.id ? "Cancel" : "Reply"}</span>
                    </button>
                  </div>

                  {/* Inline Reply Composer */}
                  {replyingToId === comment.id && (
                    <div className="pl-9 pt-2 space-y-2">
                      <textarea
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        placeholder={`Reply to @${comment.author?.username}...`}
                        rows={2}
                        maxLength={500}
                        className="w-full rounded-md border p-2 text-xs bg-background focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                      <SmartRepliesBar
                        postId={post.id}
                        commentId={comment.id}
                        onSelectReply={(text) => setReplyText(text)}
                      />
                      <div className="flex justify-end">
                        <Button
                          size="sm"
                          onClick={() => handleReplySubmit(comment.id)}
                          disabled={!replyText.trim() || addCommentMutation.isPending}
                          className="h-7 text-xs"
                        >
                          Send Reply
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Nested 1-Level Replies */}
                  {comment.replies && comment.replies.length > 0 && (
                    <div className="pl-6 sm:pl-9 space-y-2 pt-2 border-l-2 border-muted ml-3 sm:ml-4">
                      {comment.replies.map((reply) => {
                        const canDeleteReply =
                          user?.id === reply.author_id || isAdmin;

                        return (
                          <div
                            key={reply.id}
                            className="rounded-lg bg-muted/40 p-2.5 space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                <Avatar className="h-5 w-5">
                                  {reply.author?.avatar_url && (
                                    <AvatarImage
                                      src={reply.author.avatar_url}
                                      alt={reply.author.display_name}
                                    />
                                  )}
                                  <AvatarFallback>
                                    {getInitials(
                                      reply.author?.display_name || "User"
                                    )}
                                  </AvatarFallback>
                                </Avatar>
                                <span className="text-xs font-semibold">
                                  {reply.author?.display_name || "Deleted User"}
                                </span>
                                <span className="text-[10px] text-muted-foreground">
                                  {timeAgo(reply.created_at)}
                                </span>
                              </div>

                              {canDeleteReply && (
                                <button
                                  onClick={() =>
                                    deleteCommentMutation.mutate(reply.id)
                                  }
                                  className="text-muted-foreground hover:text-destructive p-0.5"
                                  title="Delete reply"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              )}
                            </div>

                            <p className="text-xs text-foreground whitespace-pre-wrap pl-7">
                              {reply.content}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {!isLoadingComments && (!comments || comments.length === 0) && (
          <p className="text-center text-xs text-muted-foreground py-6">
            No comments yet. Start the conversation!
          </p>
        )}
      </div>
    </div>
  );
}
