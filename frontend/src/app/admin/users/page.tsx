"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  MoreHorizontal,
  Search,
  Shield,
  Trash2,
  UserCheck,
  UserX,
} from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { useToast } from "@/components/ui/use-toast";
import { getInitials } from "@/lib/utils";
import type { AdminUserListResponse, AdminUserResponse } from "@/types";

export default function AdminUsersPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Search & Filter State
  const [search, setSearch] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  const [roleFilter, setRoleFilter] = React.useState<string>("all");
  const [suspendFilter, setSuspendFilter] = React.useState<string>("all");
  const [page, setPage] = React.useState(1);
  const pageSize = 15;

  // Debounce search
  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [search]);

  // Dialog states
  const [suspendTarget, setSuspendTarget] = React.useState<AdminUserResponse | null>(null);
  const [suspendReason, setSuspendReason] = React.useState("");
  const [roleTarget, setRoleTarget] = React.useState<AdminUserResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<AdminUserResponse | null>(null);

  // Fetch users query
  const { data, isLoading, isError } = useQuery<AdminUserListResponse>({
    queryKey: ["admin", "users", { page, debouncedSearch, roleFilter, suspendFilter }],
    queryFn: () => {
      const params: Record<string, string | number | boolean> = {
        page,
        page_size: pageSize,
      };
      if (debouncedSearch) params.search = debouncedSearch;
      if (roleFilter !== "all") params.role = roleFilter;
      if (suspendFilter === "active") params.is_suspended = false;
      if (suspendFilter === "suspended") params.is_suspended = true;

      return apiClient.get<AdminUserListResponse>("/admin/users", params);
    },
  });

  // 1. Suspend / Unsuspend Mutation
  const suspendMutation = useMutation({
    mutationFn: ({ userId, isSuspended, reason }: { userId: string; isSuspended: boolean; reason?: string }) =>
      apiClient.patch(`/admin/users/${userId}/suspend`, { is_suspended: isSuspended, reason }),
    onSuccess: (_, variables) => {
      toast({
        title: variables.isSuspended ? "Account Suspended" : "Account Unsuspended",
        description: `User account has been successfully ${variables.isSuspended ? "suspended" : "restored"}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
      setSuspendTarget(null);
      setSuspendReason("");
    },
    onError: (err: Error) => {
      toast({
        variant: "destructive",
        title: "Action Failed",
        description: err.message || "Failed to update account suspension status.",
      });
    },
  });

  // 2. Change Role Mutation
  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: "user" | "admin" }) =>
      apiClient.patch(`/admin/users/${userId}/role`, { role }),
    onSuccess: (_, variables) => {
      toast({
        title: "Role Updated",
        description: `User role changed to ${variables.role}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      setRoleTarget(null);
    },
    onError: (err: Error) => {
      toast({
        variant: "destructive",
        title: "Role Update Failed",
        description: err.message || "Failed to modify user role.",
      });
    },
  });

  // 3. Delete User Mutation
  const deleteMutation = useMutation({
    mutationFn: (userId: string) => apiClient.delete(`/admin/users/${userId}`),
    onSuccess: () => {
      toast({
        title: "User Deleted",
        description: "User account and all associated data permanently deleted.",
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
      setDeleteTarget(null);
    },
    onError: (err: Error) => {
      toast({
        variant: "destructive",
        title: "Deletion Failed",
        description: err.message || "Failed to delete user account.",
      });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">User Administration</h1>
          <p className="text-sm text-muted-foreground">
            Manage account permissions, suspensions, and platform users
          </p>
        </div>
        <div className="text-sm text-muted-foreground">
          Total Users: <span className="font-semibold text-foreground">{data?.total ?? 0}</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by username, email, or name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Role Filter */}
            <div className="w-full sm:w-[150px]">
              <Select
                value={roleFilter}
                onValueChange={(val) => {
                  setRoleFilter(val);
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Roles" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Status Filter */}
            <div className="w-full sm:w-[160px]">
              <Select
                value={suspendFilter}
                onValueChange={(val) => {
                  setSuspendFilter(val);
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="active">Active Only</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-center">Activity</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7} className="h-14 animate-pulse bg-muted/20" />
                  </TableRow>
                ))
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-destructive">
                    Failed to load users list.
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                    No users matching criteria.
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((u) => (
                  <TableRow key={u.id} className="hover:bg-muted/40">
                    {/* User Profile */}
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarImage src={`https://avatar.vercel.sh/${u.username}`} />
                          <AvatarFallback className="text-xs">
                            {getInitials(u.display_name)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium text-foreground leading-none">
                            {u.display_name}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5">@{u.username}</p>
                        </div>
                      </div>
                    </TableCell>

                    {/* Email */}
                    <TableCell>
                      <div className="flex items-center gap-1.5 text-sm">
                        <span>{u.email}</span>
                        {u.is_verified ? (
                          <span title="Email verified">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                          </span>
                        ) : (
                          <Badge variant="outline" className="text-[10px] px-1 py-0 text-amber-500 border-amber-500/30">
                            Unverified
                          </Badge>
                        )}
                      </div>
                    </TableCell>

                    {/* Role */}
                    <TableCell>
                      {u.role === "admin" ? (
                        <Badge className="bg-indigo-600 text-white hover:bg-indigo-700">
                          <Shield className="mr-1 h-3 w-3" /> Admin
                        </Badge>
                      ) : (
                        <Badge variant="secondary">User</Badge>
                      )}
                    </TableCell>

                    {/* Status */}
                    <TableCell>
                      {u.is_suspended ? (
                        <Badge variant="destructive" className="flex items-center gap-1 w-fit">
                          <UserX className="h-3 w-3" /> Suspended
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-emerald-600 border-emerald-500/30 bg-emerald-500/10 w-fit flex items-center gap-1">
                          <UserCheck className="h-3 w-3" /> Active
                        </Badge>
                      )}
                    </TableCell>

                    {/* Activity Stats */}
                    <TableCell className="text-center text-xs text-muted-foreground">
                      <span className="font-semibold text-foreground">{u.posts_count}</span> posts ·{" "}
                      <span className="font-semibold text-foreground">{u.comments_count}</span> comments
                    </TableCell>

                    {/* Joined Date */}
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(u.created_at).toLocaleDateString()}
                    </TableCell>

                    {/* Actions Menu */}
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Account Controls</DropdownMenuLabel>
                          <DropdownMenuSeparator />

                          {/* Role Toggle */}
                          <DropdownMenuItem onClick={() => setRoleTarget(u)}>
                            <Shield className="mr-2 h-4 w-4" />
                            {u.role === "admin" ? "Demote to User" : "Promote to Admin"}
                          </DropdownMenuItem>

                          {/* Suspend Toggle */}
                          <DropdownMenuItem
                            onClick={() => {
                              setSuspendTarget(u);
                              setSuspendReason("");
                            }}
                            className={u.is_suspended ? "text-emerald-600" : "text-amber-600"}
                          >
                            {u.is_suspended ? (
                              <>
                                <UserCheck className="mr-2 h-4 w-4" /> Unsuspend Account
                              </>
                            ) : (
                              <>
                                <UserX className="mr-2 h-4 w-4" /> Suspend Account
                              </>
                            )}
                          </DropdownMenuItem>

                          <DropdownMenuSeparator />

                          {/* Delete Account */}
                          <DropdownMenuItem
                            onClick={() => setDeleteTarget(u)}
                            className="text-destructive focus:text-destructive"
                          >
                            <Trash2 className="mr-2 h-4 w-4" /> Delete Account
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination Controls */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.total_pages} ({data.total} total accounts)
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(p - 1, 1))}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4 mr-1" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(p + 1, data.total_pages))}
              disabled={page >= data.total_pages}
            >
              Next <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Suspend Confirmation Dialog */}
      <Dialog open={!!suspendTarget} onOpenChange={(open) => !open && setSuspendTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {suspendTarget?.is_suspended ? "Unsuspend User Account" : "Suspend User Account"}
            </DialogTitle>
            <DialogDescription>
              {suspendTarget?.is_suspended
                ? `Restore full access for @${suspendTarget?.username}. They will immediately be able to log in and post.`
                : `Suspend @${suspendTarget?.username}. Their active sessions will be terminated and they will be blocked from accessing the platform.`}
            </DialogDescription>
          </DialogHeader>

          {!suspendTarget?.is_suspended && (
            <div className="space-y-2 py-2">
              <Label htmlFor="suspendReason">Suspension Reason (Internal / Audit)</Label>
              <Input
                id="suspendReason"
                placeholder="e.g. Repeated policy violation, hate speech..."
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
              />
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setSuspendTarget(null)}>
              Cancel
            </Button>
            <Button
              variant={suspendTarget?.is_suspended ? "default" : "destructive"}
              disabled={suspendMutation.isPending}
              onClick={() => {
                if (suspendTarget) {
                  suspendMutation.mutate({
                    userId: suspendTarget.id,
                    isSuspended: !suspendTarget.is_suspended,
                    reason: suspendReason || undefined,
                  });
                }
              }}
            >
              {suspendMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {suspendTarget?.is_suspended ? "Unsuspend Account" : "Suspend Account"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Role Change Confirmation Dialog */}
      <Dialog open={!!roleTarget} onOpenChange={(open) => !open && setRoleTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {roleTarget?.role === "admin" ? "Demote Admin to User" : "Promote User to Admin"}
            </DialogTitle>
            <DialogDescription>
              {roleTarget?.role === "admin"
                ? `Remove administrator privileges from @${roleTarget?.username}. They will no longer have access to this control console.`
                : `Grant full administrative privileges to @${roleTarget?.username}. They will be able to manage users, moderate content, and inspect audit logs.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleTarget(null)}>
              Cancel
            </Button>
            <Button
              disabled={roleMutation.isPending}
              onClick={() => {
                if (roleTarget) {
                  roleMutation.mutate({
                    userId: roleTarget.id,
                    role: roleTarget.role === "admin" ? "user" : "admin",
                  });
                }
              }}
            >
              {roleMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Confirm Role Change
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" /> Permanently Delete User
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently delete account @{deleteTarget?.username}?
              This action is irreversible and cascades to all authored posts, comments, likes, and sessions.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => {
                if (deleteTarget) {
                  deleteMutation.mutate(deleteTarget.id);
                }
              }}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete Account Permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
