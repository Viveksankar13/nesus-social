"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  FileText,
  ImageIcon,
  Loader2,
  MessageCircle,
  MoreHorizontal,
  Search,
  Trash2,
} from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { truncate } from "@/lib/utils";
import type {
  AdminCommentListResponse,
  AdminCommentResponse,
  AdminPostListResponse,
  AdminPostResponse,
} from "@/types";

export default function AdminContentPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [activeTab, setActiveTab] = React.useState<"posts" | "comments">("posts");

  // Post State
  const [postSearch, setPostSearch] = React.useState("");
  const [postDebouncedSearch, setPostDebouncedSearch] = React.useState("");
  const [postHiddenFilter, setPostHiddenFilter] = React.useState<string>("all");
  const [postPage, setPostPage] = React.useState(1);
  const [selectedPostIds, setSelectedPostIds] = React.useState<string[]>([]);
  const [deletePostTarget, setDeletePostTarget] = React.useState<AdminPostResponse | null>(null);

  // Comment State
  const [commentSearch, setCommentSearch] = React.useState("");
  const [commentDebouncedSearch, setCommentDebouncedSearch] = React.useState("");
  const [commentHiddenFilter, setCommentHiddenFilter] = React.useState<string>("all");
  const [commentPage, setCommentPage] = React.useState(1);
  const [selectedCommentIds, setSelectedCommentIds] = React.useState<string[]>([]);
  const [deleteCommentTarget, setDeleteCommentTarget] = React.useState<AdminCommentResponse | null>(null);

  // Debounce search
  React.useEffect(() => {
    const handler = setTimeout(() => {
      setPostDebouncedSearch(postSearch);
      setPostPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [postSearch]);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setCommentDebouncedSearch(commentSearch);
      setCommentPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [commentSearch]);

  // 1. Fetch Posts Query
  const {
    data: postsData,
    isLoading: postsLoading,
    isError: postsError,
  } = useQuery<AdminPostListResponse>({
    queryKey: ["admin", "posts", { postPage, postDebouncedSearch, postHiddenFilter }],
    queryFn: () => {
      const params: Record<string, string | number | boolean> = {
        page: postPage,
        page_size: 15,
      };
      if (postDebouncedSearch) params.search = postDebouncedSearch;
      if (postHiddenFilter === "public") params.is_hidden = false;
      if (postHiddenFilter === "hidden") params.is_hidden = true;
      return apiClient.get<AdminPostListResponse>("/admin/posts", params);
    },
    enabled: activeTab === "posts",
  });

  // 2. Fetch Comments Query
  const {
    data: commentsData,
    isLoading: commentsLoading,
    isError: commentsError,
  } = useQuery<AdminCommentListResponse>({
    queryKey: ["admin", "comments", { commentPage, commentDebouncedSearch, commentHiddenFilter }],
    queryFn: () => {
      const params: Record<string, string | number | boolean> = {
        page: commentPage,
        page_size: 15,
      };
      if (commentDebouncedSearch) params.search = commentDebouncedSearch;
      if (commentHiddenFilter === "public") params.is_hidden = false;
      if (commentHiddenFilter === "hidden") params.is_hidden = true;
      return apiClient.get<AdminCommentListResponse>("/admin/comments", params);
    },
    enabled: activeTab === "comments",
  });

  // Post Mutations
  const toggleHidePostMutation = useMutation({
    mutationFn: ({ postId, isHidden }: { postId: string; isHidden: boolean }) =>
      apiClient.patch(`/admin/posts/${postId}/hide`, { is_hidden: isHidden }),
    onSuccess: (_, variables) => {
      toast({
        title: variables.isHidden ? "Post Hidden" : "Post Restored",
        description: `Post is now ${variables.isHidden ? "hidden from feeds" : "publicly visible"}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "posts"] });
    },
  });

  const deletePostMutation = useMutation({
    mutationFn: (postId: string) => apiClient.delete(`/admin/posts/${postId}`),
    onSuccess: () => {
      toast({ title: "Post Deleted", description: "Post permanently deleted." });
      queryClient.invalidateQueries({ queryKey: ["admin", "posts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
      setDeletePostTarget(null);
    },
  });

  const bulkPostMutation = useMutation({
    mutationFn: ({ ids, action }: { ids: string[]; action: "hide" | "restore" | "delete" }) =>
      apiClient.post<{ message: string }>("/admin/posts/bulk", { ids, action }),
    onSuccess: (data) => {
      toast({ title: "Bulk Action Completed", description: data.message });
      setSelectedPostIds([]);
      queryClient.invalidateQueries({ queryKey: ["admin", "posts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });

  // Comment Mutations
  const toggleHideCommentMutation = useMutation({
    mutationFn: ({ commentId, isHidden }: { commentId: string; isHidden: boolean }) =>
      apiClient.patch(`/admin/comments/${commentId}/hide`, { is_hidden: isHidden }),
    onSuccess: (_, variables) => {
      toast({
        title: variables.isHidden ? "Comment Hidden" : "Comment Restored",
        description: `Comment is now ${variables.isHidden ? "hidden" : "visible"}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "comments"] });
    },
  });

  const deleteCommentMutation = useMutation({
    mutationFn: (commentId: string) => apiClient.delete(`/admin/comments/${commentId}`),
    onSuccess: () => {
      toast({ title: "Comment Deleted", description: "Comment permanently deleted." });
      queryClient.invalidateQueries({ queryKey: ["admin", "comments"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
      setDeleteCommentTarget(null);
    },
  });

  const bulkCommentMutation = useMutation({
    mutationFn: ({ ids, action }: { ids: string[]; action: "hide" | "restore" | "delete" }) =>
      apiClient.post<{ message: string }>("/admin/comments/bulk", { ids, action }),
    onSuccess: (data) => {
      toast({ title: "Bulk Action Completed", description: data.message });
      setSelectedCommentIds([]);
      queryClient.invalidateQueries({ queryKey: ["admin", "comments"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });

  const handleSelectAllPosts = (checked: boolean) => {
    if (checked && postsData) {
      setSelectedPostIds(postsData.items.map((p) => p.id));
    } else {
      setSelectedPostIds([]);
    }
  };

  const handleSelectAllComments = (checked: boolean) => {
    if (checked && commentsData) {
      setSelectedCommentIds(commentsData.items.map((c) => c.id));
    } else {
      setSelectedCommentIds([]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Content Management</h1>
        <p className="text-sm text-muted-foreground">
          Inspect public and hidden posts and comments, perform bulk moderation
        </p>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(val) => setActiveTab(val as "posts" | "comments")}
        className="space-y-4"
      >
        <TabsList>
          <TabsTrigger value="posts" className="gap-2">
            <FileText className="h-4 w-4" />
            Posts ({postsData?.total ?? 0})
          </TabsTrigger>
          <TabsTrigger value="comments" className="gap-2">
            <MessageCircle className="h-4 w-4" />
            Comments ({commentsData?.total ?? 0})
          </TabsTrigger>
        </TabsList>

        {/* ── Posts Tab ──────────────────────────────────────────────────────── */}
        <TabsContent value="posts" className="space-y-4">
          {/* Controls & Bulk Bar */}
          <Card>
            <CardContent className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-1 items-center gap-3">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search post content..."
                    value={postSearch}
                    onChange={(e) => setPostSearch(e.target.value)}
                    className="pl-9"
                  />
                </div>

                <div className="w-[140px]">
                  <Select
                    value={postHiddenFilter}
                    onValueChange={(val) => {
                      setPostHiddenFilter(val);
                      setPostPage(1);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All Posts" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Statuses</SelectItem>
                      <SelectItem value="public">Public</SelectItem>
                      <SelectItem value="hidden">Hidden</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Bulk Actions */}
              {selectedPostIds.length > 0 && (
                <div className="flex items-center gap-2 bg-muted/60 p-1.5 rounded-lg border border-border">
                  <span className="text-xs font-semibold px-2">
                    {selectedPostIds.length} selected
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => bulkPostMutation.mutate({ ids: selectedPostIds, action: "hide" })}
                  >
                    <EyeOff className="mr-1 h-3 w-3" /> Hide
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => bulkPostMutation.mutate({ ids: selectedPostIds, action: "restore" })}
                  >
                    <Eye className="mr-1 h-3 w-3" /> Restore
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => bulkPostMutation.mutate({ ids: selectedPostIds, action: "delete" })}
                  >
                    <Trash2 className="mr-1 h-3 w-3" /> Delete
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Posts Table */}
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12 text-center">
                      <input
                        type="checkbox"
                        checked={
                          Boolean(postsData?.items.length) &&
                          selectedPostIds.length === postsData?.items.length
                        }
                        onChange={(e) => handleSelectAllPosts(e.target.checked)}
                        className="rounded border-border"
                      />
                    </TableHead>
                    <TableHead>Author</TableHead>
                    <TableHead className="w-[45%]">Content</TableHead>
                    <TableHead className="text-center">Engagement</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {postsLoading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell colSpan={7} className="h-14 animate-pulse bg-muted/20" />
                      </TableRow>
                    ))
                  ) : postsError ? (
                    <TableRow>
                      <TableCell colSpan={7} className="h-28 text-center text-destructive">
                        Failed to load posts.
                      </TableCell>
                    </TableRow>
                  ) : postsData?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="h-28 text-center text-muted-foreground">
                        No posts found matching search criteria.
                      </TableCell>
                    </TableRow>
                  ) : (
                    postsData?.items.map((post) => {
                      const isSelected = selectedPostIds.includes(post.id);
                      return (
                        <TableRow key={post.id} className="hover:bg-muted/40">
                          <TableCell className="text-center">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedPostIds([...selectedPostIds, post.id]);
                                } else {
                                  setSelectedPostIds(selectedPostIds.filter((id) => id !== post.id));
                                }
                              }}
                              className="rounded border-border"
                            />
                          </TableCell>
                          <TableCell className="font-semibold text-foreground">
                            @{post.author_username}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {post.image_url && (
                                <span title="Includes Image">
                                  <ImageIcon className="h-4 w-4 shrink-0 text-indigo-500" />
                                </span>
                              )}
                              <p className="text-sm text-foreground leading-snug line-clamp-2">
                                {truncate(post.content, 120)}
                              </p>
                            </div>
                          </TableCell>
                          <TableCell className="text-center text-xs text-muted-foreground whitespace-nowrap">
                            <span className="font-semibold text-foreground">{post.likes_count}</span> likes ·{" "}
                            <span className="font-semibold text-foreground">{post.comments_count}</span> replies
                          </TableCell>
                          <TableCell>
                            {post.is_hidden ? (
                              <Badge variant="destructive" className="text-xs">
                                Hidden
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-emerald-600 border-emerald-500/30 bg-emerald-500/10 text-xs">
                                Public
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(post.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onClick={() =>
                                    toggleHidePostMutation.mutate({
                                      postId: post.id,
                                      isHidden: !post.is_hidden,
                                    })
                                  }
                                >
                                  {post.is_hidden ? (
                                    <>
                                      <Eye className="mr-2 h-4 w-4" /> Restore Post
                                    </>
                                  ) : (
                                    <>
                                      <EyeOff className="mr-2 h-4 w-4" /> Hide from Feed
                                    </>
                                  )}
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() => setDeletePostTarget(post)}
                                  className="text-destructive focus:text-destructive"
                                >
                                  <Trash2 className="mr-2 h-4 w-4" /> Delete Post
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Post Pagination */}
          {postsData && postsData.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {postsData.page} of {postsData.total_pages} ({postsData.total} posts)
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPostPage((p) => Math.max(p - 1, 1))}
                  disabled={postPage <= 1}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" /> Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPostPage((p) => Math.min(p + 1, postsData.total_pages))}
                  disabled={postPage >= postsData.total_pages}
                >
                  Next <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </TabsContent>

        {/* ── Comments Tab ───────────────────────────────────────────────────── */}
        <TabsContent value="comments" className="space-y-4">
          <Card>
            <CardContent className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-1 items-center gap-3">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search comment text..."
                    value={commentSearch}
                    onChange={(e) => setCommentSearch(e.target.value)}
                    className="pl-9"
                  />
                </div>

                <div className="w-[140px]">
                  <Select
                    value={commentHiddenFilter}
                    onValueChange={(val) => {
                      setCommentHiddenFilter(val);
                      setCommentPage(1);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All Comments" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Statuses</SelectItem>
                      <SelectItem value="public">Public</SelectItem>
                      <SelectItem value="hidden">Hidden</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Bulk Comment Actions */}
              {selectedCommentIds.length > 0 && (
                <div className="flex items-center gap-2 bg-muted/60 p-1.5 rounded-lg border border-border">
                  <span className="text-xs font-semibold px-2">
                    {selectedCommentIds.length} selected
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => bulkCommentMutation.mutate({ ids: selectedCommentIds, action: "hide" })}
                  >
                    <EyeOff className="mr-1 h-3 w-3" /> Hide
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => bulkCommentMutation.mutate({ ids: selectedCommentIds, action: "restore" })}
                  >
                    <Eye className="mr-1 h-3 w-3" /> Restore
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => bulkCommentMutation.mutate({ ids: selectedCommentIds, action: "delete" })}
                  >
                    <Trash2 className="mr-1 h-3 w-3" /> Delete
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12 text-center">
                      <input
                        type="checkbox"
                        checked={
                          Boolean(commentsData?.items.length) &&
                          selectedCommentIds.length === commentsData?.items.length
                        }
                        onChange={(e) => handleSelectAllComments(e.target.checked)}
                        className="rounded border-border"
                      />
                    </TableHead>
                    <TableHead>Author</TableHead>
                    <TableHead className="w-[50%]">Comment Content</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {commentsLoading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell colSpan={7} className="h-14 animate-pulse bg-muted/20" />
                      </TableRow>
                    ))
                  ) : commentsError ? (
                    <TableRow>
                      <TableCell colSpan={7} className="h-28 text-center text-destructive">
                        Failed to load comments.
                      </TableCell>
                    </TableRow>
                  ) : commentsData?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="h-28 text-center text-muted-foreground">
                        No comments found matching search criteria.
                      </TableCell>
                    </TableRow>
                  ) : (
                    commentsData?.items.map((comment) => {
                      const isSelected = selectedCommentIds.includes(comment.id);
                      return (
                        <TableRow key={comment.id} className="hover:bg-muted/40">
                          <TableCell className="text-center">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedCommentIds([...selectedCommentIds, comment.id]);
                                } else {
                                  setSelectedCommentIds(
                                    selectedCommentIds.filter((id) => id !== comment.id)
                                  );
                                }
                              }}
                              className="rounded border-border"
                            />
                          </TableCell>
                          <TableCell className="font-semibold text-foreground">
                            @{comment.author_username || "Deleted User"}
                          </TableCell>
                          <TableCell>
                            <p className="text-sm text-foreground line-clamp-2">
                              {truncate(comment.content, 140)}
                            </p>
                          </TableCell>
                          <TableCell>
                            {comment.parent_id ? (
                              <Badge variant="secondary" className="text-[11px]">
                                Reply
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-[11px]">
                                Top Level
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            {comment.is_hidden ? (
                              <Badge variant="destructive" className="text-xs">
                                Hidden
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-emerald-600 border-emerald-500/30 bg-emerald-500/10 text-xs">
                                Public
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(comment.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onClick={() =>
                                    toggleHideCommentMutation.mutate({
                                      commentId: comment.id,
                                      isHidden: !comment.is_hidden,
                                    })
                                  }
                                >
                                  {comment.is_hidden ? (
                                    <>
                                      <Eye className="mr-2 h-4 w-4" /> Restore Comment
                                    </>
                                  ) : (
                                    <>
                                      <EyeOff className="mr-2 h-4 w-4" /> Hide Comment
                                    </>
                                  )}
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() => setDeleteCommentTarget(comment)}
                                  className="text-destructive focus:text-destructive"
                                >
                                  <Trash2 className="mr-2 h-4 w-4" /> Delete Comment
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Comment Pagination */}
          {commentsData && commentsData.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {commentsData.page} of {commentsData.total_pages} ({commentsData.total} comments)
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCommentPage((p) => Math.max(p - 1, 1))}
                  disabled={commentPage <= 1}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" /> Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCommentPage((p) => Math.min(p + 1, commentsData.total_pages))}
                  disabled={commentPage >= commentsData.total_pages}
                >
                  Next <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Delete Post Dialog */}
      <Dialog open={!!deletePostTarget} onOpenChange={(open) => !open && setDeletePostTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" /> Permanently Delete Post
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this post by @{deletePostTarget?.author_username}?
              All comments and reactions on this post will also be deleted.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md bg-muted p-3 text-sm italic border">
            &ldquo;{deletePostTarget?.content}&rdquo;
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletePostTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deletePostMutation.isPending}
              onClick={() => deletePostTarget && deletePostMutation.mutate(deletePostTarget.id)}
            >
              {deletePostMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete Post
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Comment Dialog */}
      <Dialog open={!!deleteCommentTarget} onOpenChange={(open) => !open && setDeleteCommentTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" /> Permanently Delete Comment
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this comment? Any direct replies will also be deleted.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md bg-muted p-3 text-sm italic border">
            &ldquo;{deleteCommentTarget?.content}&rdquo;
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteCommentTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteCommentMutation.isPending}
              onClick={() => deleteCommentTarget && deleteCommentMutation.mutate(deleteCommentTarget.id)}
            >
              {deleteCommentMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete Comment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
