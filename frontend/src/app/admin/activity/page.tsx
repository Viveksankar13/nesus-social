"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Code2,
  Filter,
  Globe,
  Shield,
} from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import type { ActivityLogListResponse, ActivityLogResponse } from "@/types";

export default function AdminActivityPage() {
  const [actionFilter, setActionFilter] = React.useState<string>("all");
  const [resourceFilter, setResourceFilter] = React.useState<string>("all");
  const [page, setPage] = React.useState(1);
  const pageSize = 20;

  // Selected Log for JSON inspector
  const [inspectTarget, setInspectTarget] = React.useState<ActivityLogResponse | null>(null);

  // Fetch Activity Logs Query
  const { data, isLoading, isError } = useQuery<ActivityLogListResponse>({
    queryKey: ["admin", "activity-logs", { page, actionFilter, resourceFilter }],
    queryFn: () => {
      const params: Record<string, string | number | boolean> = {
        page,
        page_size: pageSize,
      };
      if (actionFilter !== "all") params.action = actionFilter;
      if (resourceFilter !== "all") params.resource_type = resourceFilter;
      return apiClient.get<ActivityLogListResponse>("/admin/activity-logs", params);
    },
  });

  const getActionBadge = (action: string) => {
    if (action.includes("delete")) {
      return <Badge variant="destructive" className="text-xs">{action}</Badge>;
    }
    if (action.includes("suspend")) {
      return <Badge className="bg-amber-500/20 text-amber-600 border border-amber-500/30 text-xs">{action}</Badge>;
    }
    if (action.includes("role")) {
      return <Badge className="bg-indigo-500/20 text-indigo-600 border border-indigo-500/30 text-xs">{action}</Badge>;
    }
    return <Badge variant="secondary" className="text-xs">{action}</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Activity Audit Logs</h1>
          <p className="text-sm text-muted-foreground">
            Immutable administrative action history and security audit trail
          </p>
        </div>
        <div className="text-sm text-muted-foreground">
          Total Recorded Actions: <span className="font-semibold text-foreground">{data?.total ?? 0}</span>
        </div>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
            <Filter className="h-4 w-4" /> Filter by:
          </div>

          <div className="w-full sm:w-[200px]">
            <Select
              value={actionFilter}
              onValueChange={(val) => {
                setActionFilter(val);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="All Actions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actions</SelectItem>
                <SelectItem value="suspend_user">suspend_user</SelectItem>
                <SelectItem value="unsuspend_user">unsuspend_user</SelectItem>
                <SelectItem value="update_user_role">update_user_role</SelectItem>
                <SelectItem value="delete_user">delete_user</SelectItem>
                <SelectItem value="hide_post">hide_post</SelectItem>
                <SelectItem value="restore_post">restore_post</SelectItem>
                <SelectItem value="delete_post">delete_post</SelectItem>
                <SelectItem value="bulk_posts_action">bulk_posts_action</SelectItem>
                <SelectItem value="hide_comment">hide_comment</SelectItem>
                <SelectItem value="restore_comment">restore_comment</SelectItem>
                <SelectItem value="delete_comment">delete_comment</SelectItem>
                <SelectItem value="bulk_comments_action">bulk_comments_action</SelectItem>
                <SelectItem value="moderation_action">moderation_action</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="w-full sm:w-[160px]">
            <Select
              value={resourceFilter}
              onValueChange={(val) => {
                setResourceFilter(val);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="All Resources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Resources</SelectItem>
                <SelectItem value="user">User</SelectItem>
                <SelectItem value="post">Post</SelectItem>
                <SelectItem value="comment">Comment</SelectItem>
                <SelectItem value="moderation">Moderation</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Administrator</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Resource ID</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead className="text-right">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7} className="h-12 animate-pulse bg-muted/20" />
                  </TableRow>
                ))
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-28 text-center text-destructive">
                    Failed to load activity logs.
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                    <Activity className="mx-auto h-8 w-8 text-muted-foreground mb-2 opacity-50" />
                    No activity logs recorded matching criteria.
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((log) => (
                  <TableRow key={log.id} className="hover:bg-muted/40">
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Shield className="h-3.5 w-3.5 text-indigo-500" />
                        <span className="font-semibold text-foreground text-sm">
                          @{log.admin_username || "system"}
                        </span>
                      </div>
                    </TableCell>

                    <TableCell>{getActionBadge(log.action)}</TableCell>

                    <TableCell>
                      <Badge variant="outline" className="capitalize text-xs font-medium">
                        {log.resource_type}
                      </Badge>
                    </TableCell>

                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {log.resource_id ? `${log.resource_id.slice(0, 8)}...` : "—"}
                    </TableCell>

                    <TableCell className="text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Globe className="h-3 w-3 opacity-60" />
                        <span>{log.ip_address || "127.0.0.1"}</span>
                      </div>
                    </TableCell>

                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>

                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 gap-1 text-xs text-indigo-600 hover:text-indigo-700"
                        onClick={() => setInspectTarget(log)}
                      >
                        <Code2 className="h-3.5 w-3.5" /> Inspect
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.total_pages} ({data.total} recorded actions)
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

      {/* JSON Inspector Dialog */}
      <Dialog open={!!inspectTarget} onOpenChange={(open) => !open && setInspectTarget(null)}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Code2 className="h-5 w-5 text-indigo-600" />
              Audit Log Details
            </DialogTitle>
            <DialogDescription>
              Action: <span className="font-semibold text-foreground">{inspectTarget?.action}</span> ·
              Admin: @{inspectTarget?.admin_username || "system"} ·
              Resource: {inspectTarget?.resource_type} ({inspectTarget?.resource_id ?? "N/A"})
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-96 overflow-y-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs text-zinc-100 border border-zinc-800">
            <pre>{JSON.stringify(inspectTarget?.details ?? {}, null, 2)}</pre>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
