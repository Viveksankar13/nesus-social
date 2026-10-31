"use client";

import * as React from "react";
import Link from "next/link";
import {
  Heart,
  MessageCircle,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { SwapPostCard } from "@/components/swaps/swap-post-card";
import { getInitials, timeAgo } from "@/lib/utils";
import type { LikeResponse, Post } from "@/types";

interface PostCardProps {
  post: Post;
  showCommentsLink?: boolean;
}

export function PostCard({ post, showCommentsLink = true }: PostCardProps) {
  const { user, isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Optimistic like state
  const [hasLiked, setHasLiked] = React.useState(post.has_liked);
  const [likesCount, setLikesCount] = React.useState(post.likes_count);

  // Edit dialog state
  const [isEditDialogOpen, setIsEditDialogOpen] = React.useState(false);
  const [editContent, setEditContent] = React.useState(post.content);
  const [editImageUrl, setEditImageUrl] = React.useState(post.image_url || "");

  // Delete dialog state
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false);

  const isOwner = user?.id === post.author_id;
  const canModify = isOwner || isAdmin;

  // Like mutation with optimistic update
  const likeMutation = useMutation({
    mutationFn: () => apiClient.post<LikeResponse>(`/posts/${post.id}/like`),
    onMutate: async () => {
      const prevLiked = hasLiked;
      const prevCount = likesCount;

      setHasLiked(!prevLiked);
      setLikesCount(prevLiked ? Math.max(0, prevCount - 1) : prevCount + 1);

      return { prevLiked, prevCount };
    },
    onError: (err, _, context) => {
      if (context) {
        setHasLiked(context.prevLiked);
        setLikesCount(context.prevCount);
      }
      toast({
        title: "Action failed",
        description: "Could not update like status.",
        variant: "destructive",
      });
    },
    onSuccess: (data) => {
      setHasLiked(data.liked);
      setLikesCount(data.likes_count);
    },
  });

  // Edit mutation
  const editMutation = useMutation({
    mutationFn: (data: { content: string; image_url?: string | null }) =>
      apiClient.put<Post>(`/posts/${post.id}`, data),
    onSuccess: () => {
      setIsEditDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["posts"] });
      toast({ title: "Post updated successfully!" });
    },
    onError: (err: Error) => {
      toast({
        title: "Failed to update post",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => apiClient.delete(`/posts/${post.id}`),
    onSuccess: () => {
      setIsDeleteDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["posts"] });
      toast({ title: "Post deleted" });
    },
    onError: (err: Error) => {
      toast({
        title: "Failed to delete post",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editContent.trim()) return;
    editMutation.mutate({
      content: editContent.trim(),
      image_url: editImageUrl.trim() || null,
    });
  };

  return (
    <>
      <Card className="border shadow-sm mb-4 transition-all hover:border-border/80">
        <CardHeader className="p-4 sm:p-5 pb-3">
          <div className="flex items-start justify-between">
            <Link
              href={`/profile/${post.author.username}`}
              className="flex items-center space-x-3 group"
            >
              <Avatar className="h-10 w-10">
                {post.author.avatar_url && (
                  <AvatarImage
                    src={post.author.avatar_url}
                    alt={post.author.display_name}
                  />
                )}
                <AvatarFallback>
                  {getInitials(post.author.display_name)}
                </AvatarFallback>
              </Avatar>

              <div>
                <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                  {post.author.display_name}
                </p>
                <div className="flex items-center space-x-1.5 text-xs text-muted-foreground">
                  <span>@{post.author.username}</span>
                  <span>·</span>
                  <span title={new Date(post.created_at).toLocaleString()}>
                    {timeAgo(post.created_at)}
                  </span>
                  {post.is_edited && (
                    <>
                      <span>·</span>
                      <span className="italic text-[11px] text-muted-foreground/70">
                        edited
                      </span>
                    </>
                  )}
                </div>
              </div>
            </Link>

            {canModify && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                    <span className="sr-only">Post options</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onClick={() => {
                      setEditContent(post.content);
                      setEditImageUrl(post.image_url || "");
                      setIsEditDialogOpen(true);
                    }}
                    className="cursor-pointer"
                  >
                    <Pencil className="mr-2 h-4 w-4" />
                    <span>Edit Post</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => setIsDeleteDialogOpen(true)}
                    className="cursor-pointer text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    <span>Delete Post</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </CardHeader>

        <CardContent className="px-4 sm:px-5 pb-3">
          {post.content.startsWith("🔄 Skill Swap Offer:") ? (
            <SwapPostCard content={post.content} />
          ) : (
            <p className="text-sm sm:text-base text-foreground whitespace-pre-wrap leading-relaxed">
              {post.content}
            </p>
          )}

          {post.image_url && (
            <div className="mt-3 overflow-hidden rounded-xl border bg-muted">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={post.image_url}
                alt="Post attachment"
                className="w-full object-cover max-h-96"
                loading="lazy"
              />
            </div>
          )}
        </CardContent>

        <CardFooter className="px-4 sm:px-5 py-3 border-t flex items-center justify-between text-muted-foreground">
          <div className="flex items-center space-x-4">
            {/* Like button with optimistic UI */}
            <button
              onClick={() => likeMutation.mutate()}
              className={`flex items-center space-x-1.5 text-xs font-medium transition-colors hover:text-rose-500 ${
                hasLiked ? "text-rose-500" : "text-muted-foreground"
              }`}
              aria-label={hasLiked ? "Unlike post" : "Like post"}
            >
              <Heart
                className={`h-4 w-4 transition-transform active:scale-125 ${
                  hasLiked ? "fill-rose-500 text-rose-500" : ""
                }`}
              />
              <span>{likesCount}</span>
            </button>

            {/* Comments button */}
            {showCommentsLink ? (
              <Link
                href={`/posts/${post.id}`}
                className="flex items-center space-x-1.5 text-xs font-medium text-muted-foreground hover:text-primary transition-colors"
                aria-label="View comments"
              >
                <MessageCircle className="h-4 w-4" />
                <span>{post.comments_count}</span>
              </Link>
            ) : (
              <div className="flex items-center space-x-1.5 text-xs font-medium text-muted-foreground">
                <MessageCircle className="h-4 w-4" />
                <span>{post.comments_count}</span>
              </div>
            )}
          </div>
        </CardFooter>
      </Card>

      {/* Edit Post Modal */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Post</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditSubmit} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="edit_content">Post Content</Label>
              <textarea
                id="edit_content"
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows={4}
                className="w-full rounded-md border border-input bg-background p-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit_image">Image URL (Optional)</Label>
              <Input
                id="edit_image"
                type="url"
                value={editImageUrl}
                onChange={(e) => setEditImageUrl(e.target.value)}
                placeholder="https://..."
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={editMutation.isPending}>
                {editMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Post Confirmation */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Post</DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently delete this post? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <Button
              variant="outline"
              onClick={() => setIsDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete Post"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
