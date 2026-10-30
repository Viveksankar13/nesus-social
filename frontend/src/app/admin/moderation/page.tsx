"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertOctagon,
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  EyeOff,
  Filter,
  Loader2,
  ShieldAlert,
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
import { truncate } from "@/lib/utils";
import type { ModerationItemResponse, ModerationQueueResponse } from "@/types";

export default function AdminModerationPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Filters
  const [reviewedFilter, setReviewedFilter] = React.useState<string>("pending");
  const [severityFilter, setSeverityFilter] = React.useState<string>("all");
  const [page, setPage] = React.useState(1);
  const pageSize = 15;

  // Action Dialog State
  const [actionTarget, setActionTarget] = React.useState<{
    item: ModerationItemResponse;
    action: "approve" | "hide" | "delete";
  } | null>(null);
  const [actionNotes, setActionNotes] = React.useState("");

  // Query Moderation Queue
  const { data, isLoading, isError } = useQuery<ModerationQueueResponse>({
    queryKey: ["admin", "moderation", { page, reviewedFilter, severityFilter }],
    queryFn: () => {
      const params: Record<string, string | number | boolean> = {
        page,
        page_size: pageSize,
        reviewed: reviewedFilter === "resolved",
      };
      if (severityFilter !== "all") params.severity = severityFilter;
      return apiClient.get<ModerationQueueResponse>("/admin/moderation", params);
    },
  });

  // Action Mutation
  const actionMutation = useMutation({
    mutationFn: ({
      flagId,
      action,
      notes,
    }: {
      flagId: string;
      action: "approve" | "hide" | "delete";
      notes?: string;
    }) =>
      apiClient.post(`/admin/moderation/${flagId}/action`, {
        action,
        notes: notes || undefined,
      }),
    onSuccess: (_, variables) => {
      toast({
        title: "Flag Resolved",
        description: `Content flag marked as ${variables.action}d.`,
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "moderation"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
      setActionTarget(null);
      setActionNotes("");
    },
    onError: (err: Error) => {
      toast({
        variant: "destructive",
        title: "Moderation Action Failed",
        description: err.message || "Unable to resolve moderation flag.",
      });
    },
  });

  const getSeverityBadge = (severity: string, score: number) => {
    const sev = severity.toLowerCase();
    if (sev === "critical" || sev === "high") {
      return (
        <Badge variant="destructive" className="gap-1 text-xs">
          <AlertOctagon className="h-3 w-3" />
          {severity.toUpperCase()} ({score.toFixed(2)})
        </Badge>
      );
    }
    if (sev === "medium") {
      return (
        <Badge className="bg-amber-500/20 text-amber-600 border border-amber-500/30 gap-1 text-xs">
          <AlertTriangle className="h-3 w-3" />
          MEDIUM ({score.toFixed(2)})
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="gap-1 text-xs">
        LOW ({score.toFixed(2)})
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI Moderation Queue</h1>
          <p className="text-sm text-muted-foreground">
            Review and resolve content flagged by Gemini AI background analysis and policy filters
          </p>
        </div>
        <div className="text-sm text-muted-foreground">
          Total Flagged: <span className="font-semibold text-foreground">{data?.total ?? 0}</span>
        </div>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
            <Filter className="h-4 w-4" /> Filter by:
          </div>

          <div className="w-full sm:w-[160px]">
            <Select
              value={reviewedFilter}
              onValueChange={(val) => {
                setReviewedFilter(val);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Queue Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">Pending Review</SelectItem>
                <SelectItem value="resolved">Resolved / Reviewed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="w-full sm:w-[160px]">
            <Select
              value={severityFilter}
              onValueChange={(val) => {
                setSeverityFilter(val);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="All Severities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Queue Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead className="w-[35%]">Flagged Snippet</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>AI Score</TableHead>
                <TableHead className="w-[20%]">AI Reason</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7} className="h-14 animate-pulse bg-muted/20" />
                  </TableRow>
                ))
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-28 text-center text-destructive">
                    Failed to load moderation items.
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                    <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500 mb-2 opacity-80" />
                    No flagged items in this queue. Everything looks clean!
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((item) => (
                  <TableRow key={item.id} className="hover:bg-muted/40">
                    <TableCell>
                      <Badge variant="outline" className="capitalize text-xs font-semibold">
                        {item.content_type}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      <p className="text-sm text-foreground line-clamp-2 italic">
                        &ldquo;{truncate(item.content_snippet || "(No snippet available)", 120)}&rdquo;
                      </p>
                      <span className="text-[10px] text-muted-foreground">ID: {item.content_id}</span>
                    </TableCell>

                    <TableCell>
                      <Badge variant="secondary" className="text-xs uppercase">
                        {item.category}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      {getSeverityBadge(item.severity, item.score)}
                    </TableCell>

                    <TableCell>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {item.reason}
                      </p>
                    </TableCell>

                    <TableCell>
                      {item.reviewed ? (
                        <Badge variant="outline" className="text-muted-foreground text-xs">
                          Resolved ({item.action})
                        </Badge>
                      ) : (
                        <Badge className="bg-amber-500 text-white text-xs">
                          Pending
                        </Badge>
                      )}
                    </TableCell>

                    <TableCell className="text-right whitespace-nowrap">
                      {!item.reviewed ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs text-emerald-600 hover:text-emerald-700"
                            onClick={() => {
                              setActionTarget({ item, action: "approve" });
                              setActionNotes("");
                            }}
                          >
                            <Check className="mr-1 h-3 w-3" /> Approve
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs text-amber-600 hover:text-amber-700"
                            onClick={() => {
                              setActionTarget({ item, action: "hide" });
                              setActionNotes("");
                            }}
                          >
                            <EyeOff className="mr-1 h-3 w-3" /> Hide
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => {
                              setActionTarget({ item, action: "delete" });
                              setActionNotes("");
                            }}
                          >
                            <Trash2 className="mr-1 h-3 w-3" /> Delete
                          </Button>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground italic">No actions needed</span>
                      )}
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
            Page {data.page} of {data.total_pages} ({data.total} flagged items)
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

      {/* Resolution Confirmation Dialog */}
      <Dialog open={!!actionTarget} onOpenChange={(open) => !open && setActionTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 capitalize">
              <ShieldAlert className="h-5 w-5 text-indigo-600" />
              {actionTarget?.action} Content
            </DialogTitle>
            <DialogDescription>
              {actionTarget?.action === "approve"
                ? "Dismiss this flag as safe or false positive. The content will remain publicly visible."
                : actionTarget?.action === "hide"
                ? "Soft-hide this content from public feeds. The author can still see it in their private list."
                : "Permanently delete this content and its discussion replies from the database. Irreversible."}
            </DialogDescription>
          </DialogHeader>

          {actionTarget?.item.content_snippet && (
            <div className="rounded-md bg-muted p-3 text-sm italic border">
              &ldquo;{actionTarget.item.content_snippet}&rdquo;
            </div>
          )}

          <div className="space-y-2 py-2">
            <Label htmlFor="actionNotes">Resolution Notes (Optional)</Label>
            <Input
              id="actionNotes"
              placeholder="e.g. Approved: Satirical context verified..."
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setActionTarget(null)}>
              Cancel
            </Button>
            <Button
              variant={
                actionTarget?.action === "delete"
                  ? "destructive"
                  : actionTarget?.action === "hide"
                  ? "default"
                  : "outline"
              }
              disabled={actionMutation.isPending}
              onClick={() => {
                if (actionTarget) {
                  actionMutation.mutate({
                    flagId: actionTarget.item.id,
                    action: actionTarget.action,
                    notes: actionNotes,
                  });
                }
              }}
            >
              {actionMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Confirm {actionTarget?.action}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
