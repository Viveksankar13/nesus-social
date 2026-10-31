"use client";

import React, { useEffect, useState } from "react";
import {
  ArrowLeftRight,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCw,
  Sparkles,
  TrendingUp,
  XCircle,
  GitMerge,
  Filter,
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

import { swapApi } from "@/lib/swap-api";
import {
  Skill,
  SwapAdminStats,
  SwapDisputeAdmin,
  SwapListingAdmin,
} from "@/types/swap";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

export default function AdminSwapsPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("overview");

  // State
  const [stats, setStats] = useState<SwapAdminStats | null>(null);
  const [listings, setListings] = useState<SwapListingAdmin[]>([]);
  const [disputes, setDisputes] = useState<SwapDisputeAdmin[]>([]);
  const [taxonomy, setTaxonomy] = useState<Skill[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [listingFilter, setListingFilter] = useState("all");
  const [disputeFilter, setDisputeFilter] = useState("all");
  const [taxonomyFilter, setTaxonomyFilter] = useState("all");

  // Dispute resolution dialog
  const [selectedDispute, setSelectedDispute] = useState<SwapDisputeAdmin | null>(null);
  const [resolutionNote, setResolutionNote] = useState("");
  const [trustPenalty, setTrustPenalty] = useState(0);
  const [isResolving, setIsResolving] = useState(false);

  // Taxonomy dialog
  const [mergingSkill, setMergingSkill] = useState<Skill | null>(null);
  const [mergeTargetId, setMergeTargetId] = useState("");
  const [isMerging, setIsMerging] = useState(false);

  // Cron execution state
  const [runningJob, setRunningJob] = useState<string | null>(null);
  const [jobResult, setJobResult] = useState<{ job: string; records: number } | null>(null);

  // Load stats
  const fetchStats = async () => {
    try {
      const data = await swapApi.getAdminStats();
      setStats(data);
    } catch {
      toast({ title: "Error", description: "Failed to load swap statistics", variant: "destructive" });
    }
  };

  // Load listings
  const fetchListings = async () => {
    try {
      const statusParam = listingFilter === "all" ? undefined : listingFilter;
      const data = await swapApi.getAdminListings(statusParam);
      setListings(data);
    } catch {
      toast({ title: "Error", description: "Failed to load listings", variant: "destructive" });
    }
  };

  // Load disputes
  const fetchDisputes = async () => {
    try {
      const statusParam = disputeFilter === "all" ? undefined : disputeFilter;
      const data = await swapApi.getAdminDisputes(statusParam);
      setDisputes(data);
    } catch {
      toast({ title: "Error", description: "Failed to load disputes queue", variant: "destructive" });
    }
  };

  // Load taxonomy
  const fetchTaxonomy = async () => {
    try {
      const statusParam = taxonomyFilter === "all" ? undefined : taxonomyFilter;
      const data = await swapApi.getAdminTaxonomy(statusParam);
      setTaxonomy(data);
    } catch {
      toast({ title: "Error", description: "Failed to load taxonomy", variant: "destructive" });
    }
  };

  useEffect(() => {
    const loadAll = async () => {
      setIsLoading(true);
      await Promise.all([fetchStats(), fetchListings(), fetchDisputes(), fetchTaxonomy()]);
      setIsLoading(false);
    };
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeTab === "listings") fetchListings();
    if (activeTab === "disputes") fetchDisputes();
    if (activeTab === "taxonomy") fetchTaxonomy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, listingFilter, disputeFilter, taxonomyFilter]);

  // Action handlers
  const handleUpdateListingStatus = async (id: string, newStatus: string) => {
    try {
      await swapApi.updateAdminListingStatus(id, newStatus);
      toast({ title: "Status Updated", description: `Listing status set to ${newStatus}` });
      fetchListings();
      fetchStats();
    } catch {
      toast({ title: "Error", description: "Failed to update listing status", variant: "destructive" });
    }
  };

  const handleResolveDispute = async (status: "resolved" | "dismissed") => {
    if (!selectedDispute) return;
    setIsResolving(true);
    try {
      await swapApi.resolveAdminDispute(selectedDispute.id, {
        admin_resolution: resolutionNote || "Resolved by administrator after review.",
        status,
        trust_score_penalty: trustPenalty,
      });
      toast({ title: "Dispute Resolved", description: `Dispute marked as ${status}` });
      setSelectedDispute(null);
      setResolutionNote("");
      setTrustPenalty(0);
      fetchDisputes();
      fetchStats();
    } catch {
      toast({ title: "Error", description: "Failed to resolve dispute", variant: "destructive" });
    } finally {
      setIsResolving(false);
    }
  };

  const handleApproveSkill = async (skillId: string) => {
    try {
      await swapApi.approveAdminSkill(skillId);
      toast({ title: "Skill Approved", description: "Skill added to active taxonomy" });
      fetchTaxonomy();
    } catch {
      toast({ title: "Error", description: "Failed to approve skill", variant: "destructive" });
    }
  };

  const handleMergeSkills = async () => {
    if (!mergingSkill || !mergeTargetId) return;
    setIsMerging(true);
    try {
      await swapApi.mergeAdminSkills(mergingSkill.id, mergeTargetId);
      toast({ title: "Skills Merged", description: `Merged "${mergingSkill.display_name}" into canonical skill` });
      setMergingSkill(null);
      setMergeTargetId("");
      fetchTaxonomy();
    } catch {
      toast({ title: "Error", description: "Failed to merge skills", variant: "destructive" });
    } finally {
      setIsMerging(false);
    }
  };

  const handleRunJob = async (jobName: string) => {
    setRunningJob(jobName);
    setJobResult(null);
    try {
      const res = await swapApi.triggerAdminJob(jobName);
      toast({ title: "Job Complete", description: `Executed ${res.records_processed} record(s)` });
      setJobResult({ job: jobName, records: res.records_processed });
      fetchStats();
    } catch {
      toast({ title: "Execution Failed", description: `Failed for ${jobName}`, variant: "destructive" });
    } finally {
      setRunningJob(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <ArrowLeftRight className="h-6 w-6 text-indigo-500" />
            Skill Swap Economy Console
          </h1>
          <p className="text-sm text-muted-foreground">
            Administrative management of peer barter listings, disputes, safety thresholds, and skill taxonomy.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            fetchStats();
            if (activeTab === "listings") fetchListings();
            if (activeTab === "disputes") fetchDisputes();
            if (activeTab === "taxonomy") fetchTaxonomy();
          }}
          disabled={isLoading}
        >
          <RotateCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid grid-cols-2 md:grid-cols-5 gap-1">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="listings">
            Listings
            {listings.filter((l) => l.reports_count > 0).length > 0 && (
              <Badge variant="destructive" className="ml-2 text-xs py-0 px-1.5">
                {listings.filter((l) => l.reports_count > 0).length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="disputes">
            Disputes Queue
            {disputes.filter((d) => d.status === "pending").length > 0 && (
              <Badge variant="destructive" className="ml-2 text-xs py-0 px-1.5">
                {disputes.filter((d) => d.status === "pending").length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="taxonomy">
            Taxonomy
            {taxonomy.filter((s) => s.status === "pending").length > 0 && (
              <Badge variant="secondary" className="ml-2 text-xs py-0 px-1.5 bg-amber-500/10 text-amber-500">
                {taxonomy.filter((s) => s.status === "pending").length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="cron">Maintenance Jobs</TabsTrigger>
        </TabsList>

        {/* ── 1. Overview Tab ─────────────────────────────────────────── */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Listings</CardTitle>
                <ArrowLeftRight className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.total_active_listings ?? "--"}</div>
                <p className="text-xs text-muted-foreground mt-1">Available in local discovery</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Weekly Swaps</CardTitle>
                <TrendingUp className="h-4 w-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.swaps_this_week ?? "--"}</div>
                <p className="text-xs text-muted-foreground mt-1">Sessions booked in last 7 days</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
                <CheckCircle2 className="h-4 w-4 text-indigo-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats ? `${stats.completion_rate}%` : "--"}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {stats?.total_completed_sessions ?? 0} total completed sessions
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Dispute Rate</CardTitle>
                <AlertTriangle className="h-4 w-4 text-rose-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats ? `${stats.dispute_rate}%` : "--"}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {stats?.total_disputes ?? 0} reports / disputes on file
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Top Skills Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-500" />
                Top Traded Skills
              </CardTitle>
              <CardDescription>Most frequently offered and learned competencies</CardDescription>
            </CardHeader>
            <CardContent>
              {stats?.top_skills && stats.top_skills.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {stats.top_skills.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 bg-muted/60 border rounded-full px-3 py-1.5 text-sm"
                    >
                      <span className="font-medium">{item.skill}</span>
                      <Badge variant="secondary" className="text-xs px-1.5 py-0">
                        {item.count} users
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No skill trade activity recorded yet.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── 2. Listings Moderation Tab ──────────────────────────────── */}
        <TabsContent value="listings" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle>Swap Listings Directory</CardTitle>
                <CardDescription>
                  Review active offers, investigate reported posts, and manage listing status.
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <Select value={listingFilter} onValueChange={setListingFilter}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="paused">Paused</SelectItem>
                    <SelectItem value="removed">Removed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {listings.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No listings found for the selected filter.
                </div>
              ) : (
                <div className="divide-y rounded-md border">
                  {listings.map((item) => (
                    <div
                      key={item.id}
                      className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-muted/40 transition-colors"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-base">{item.title}</span>
                          <Badge
                            variant={
                              item.status === "active"
                                ? "default"
                                : item.status === "removed"
                                ? "destructive"
                                : "secondary"
                            }
                            className="capitalize text-xs"
                          >
                            {item.status}
                          </Badge>
                          {item.reports_count > 0 && (
                            <Badge variant="destructive" className="text-xs">
                              {item.reports_count} reports
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Posted by @{item.user.username} · Teaches:{" "}
                          <span className="font-medium text-foreground">
                            {item.skill_offered.display_name}
                          </span>{" "}
                          · Wants:{" "}
                          <span className="font-medium text-foreground">
                            {item.skill_wanted?.display_name ?? "Open"}
                          </span>
                        </p>
                      </div>

                      <div className="flex items-center gap-2 self-end md:self-center">
                        {item.status === "active" ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-rose-500 hover:text-rose-600 hover:bg-rose-50"
                            onClick={() => handleUpdateListingStatus(item.id, "removed")}
                          >
                            <XCircle className="h-4 w-4 mr-1.5" />
                            Suspend
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-emerald-500 hover:text-emerald-600 hover:bg-emerald-50"
                            onClick={() => handleUpdateListingStatus(item.id, "active")}
                          >
                            <CheckCircle2 className="h-4 w-4 mr-1.5" />
                            Reinstate
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── 3. Disputes & Reports Tab ───────────────────────────────── */}
        <TabsContent value="disputes" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle>Disputes & Safety Reports</CardTitle>
                <CardDescription>
                  Triage no-shows, payment solicitation reports, and behavioral issues.
                </CardDescription>
              </div>
              <Select value={disputeFilter} onValueChange={setDisputeFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="dismissed">Dismissed</SelectItem>
                </SelectContent>
              </Select>
            </CardHeader>
            <CardContent>
              {disputes.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No disputes or safety reports found.
                </div>
              ) : (
                <div className="divide-y rounded-md border">
                  {disputes.map((d) => (
                    <div
                      key={d.id}
                      className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-muted/40 transition-colors"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm capitalize">
                            Category: {d.category.replace("_", " ")}
                          </span>
                          <Badge
                            variant={d.status === "pending" ? "destructive" : "secondary"}
                            className="capitalize text-xs"
                          >
                            {d.status}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            Target: {d.target_type}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Reported by @{d.reporter.username} on{" "}
                          {new Date(d.created_at).toLocaleDateString()}
                        </p>
                        {d.notes && (
                          <p className="text-sm bg-muted/50 p-2 rounded text-muted-foreground italic mt-1">
                            &ldquo;{d.notes}&rdquo;
                          </p>
                        )}
                      </div>

                      {d.status === "pending" && (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => setSelectedDispute(d)}
                        >
                          Resolve Dispute
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── 4. Taxonomy Curation Tab ────────────────────────────────── */}
        <TabsContent value="taxonomy" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle>Skill Taxonomy Curation</CardTitle>
                <CardDescription>
                  Review pending user-suggested skills, approve new categories, and merge synonyms.
                </CardDescription>
              </div>
              <Select value={taxonomyFilter} onValueChange={setTaxonomyFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Skills</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="rejected">Rejected / Merged</SelectItem>
                </SelectContent>
              </Select>
            </CardHeader>
            <CardContent>
              <div className="divide-y rounded-md border">
                {taxonomy.map((s) => (
                  <div
                    key={s.id}
                    className="p-3 flex items-center justify-between gap-4 hover:bg-muted/40 transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{s.display_name}</span>
                        <Badge variant="outline" className="text-xs">
                          {s.category}
                        </Badge>
                        <Badge
                          variant={
                            s.status === "active"
                              ? "default"
                              : s.status === "pending"
                              ? "secondary"
                              : "destructive"
                          }
                          className="capitalize text-xs"
                        >
                          {s.status}
                        </Badge>
                      </div>
                      {s.aliases && s.aliases.length > 0 && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Aliases: {s.aliases.join(", ")}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {s.status === "pending" && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-emerald-600 hover:bg-emerald-50"
                          onClick={() => handleApproveSkill(s.id)}
                        >
                          <CheckCircle2 className="h-4 w-4 mr-1" />
                          Approve
                        </Button>
                      )}
                      {s.status !== "rejected" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setMergingSkill(s)}
                        >
                          <GitMerge className="h-4 w-4 mr-1" />
                          Merge
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── 5. Cron Maintenance Jobs Tab ────────────────────────────── */}
        <TabsContent value="cron" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Background Maintenance Jobs</CardTitle>
              <CardDescription>
                Trigger automated cron functions manually for testing or on-demand platform housekeeping.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {jobResult && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 rounded-md text-sm flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Successfully executed <strong>{jobResult.job}</strong>: processed {jobResult.records} record(s).
                </div>
              )}

              <div className="grid gap-3 md:grid-cols-2">
                <div className="p-4 border rounded-lg flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-sm">Auto-Expire Proposals</h4>
                    <p className="text-xs text-muted-foreground">Expires requests older than 72 hours</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={runningJob !== null}
                    onClick={() => handleRunJob("auto-expire-requests")}
                  >
                    <Play className="h-3.5 w-3.5 mr-1.5" />
                    Run
                  </Button>
                </div>

                <div className="p-4 border rounded-lg flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-sm">Auto-Complete Sessions</h4>
                    <p className="text-xs text-muted-foreground">Credits reciprocity for past sessions</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={runningJob !== null}
                    onClick={() => handleRunJob("auto-complete-sessions")}
                  >
                    <Play className="h-3.5 w-3.5 mr-1.5" />
                    Run
                  </Button>
                </div>

                <div className="p-4 border rounded-lg flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-sm">Reveal Double-Blind Reviews</h4>
                    <p className="text-xs text-muted-foreground">Unmasks reviews after 7 calendar days</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={runningJob !== null}
                    onClick={() => handleRunJob("reveal-swap-reviews")}
                  >
                    <Play className="h-3.5 w-3.5 mr-1.5" />
                    Run
                  </Button>
                </div>

                <div className="p-4 border rounded-lg flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-sm">Send Session Reminders</h4>
                    <p className="text-xs text-muted-foreground">Dispatches 24h & 15m email and SSE alerts</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={runningJob !== null}
                    onClick={() => handleRunJob("send-session-reminders")}
                  >
                    <Play className="h-3.5 w-3.5 mr-1.5" />
                    Run
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dispute Resolution Dialog */}
      <Dialog open={selectedDispute !== null} onOpenChange={(open) => !open && setSelectedDispute(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve Safety Report / Dispute</DialogTitle>
            <DialogDescription>
              Review the report from @{selectedDispute?.reporter.username} regarding {selectedDispute?.category}.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <Label>Admin Resolution Notes</Label>
              <Textarea
                placeholder="Explain the findings and administrative action taken..."
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                rows={3}
                className="mt-1"
              />
            </div>

            <div>
              <Label>Trust Score Penalty (Optional, 0-50 pts)</Label>
              <Input
                type="number"
                min={0}
                max={50}
                value={trustPenalty}
                onChange={(e) => setTrustPenalty(parseInt(e.target.value) || 0)}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Applied to reported peer if dispute is validated (e.g. 20 pts for confirmed no-show).
              </p>
            </div>
          </div>

          <DialogFooter className="flex justify-between sm:justify-between">
            <Button
              variant="outline"
              disabled={isResolving}
              onClick={() => handleResolveDispute("dismissed")}
            >
              Dismiss Report
            </Button>
            <Button
              variant="destructive"
              disabled={isResolving}
              onClick={() => handleResolveDispute("resolved")}
            >
              Resolve & Penalize
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Merge Skill Dialog */}
      <Dialog open={mergingSkill !== null} onOpenChange={(open) => !open && setMergingSkill(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Merge Skill: {mergingSkill?.display_name}</DialogTitle>
            <DialogDescription>
              Select the canonical active skill to merge this skill into. Listings and profiles will be re-linked.
            </DialogDescription>
          </DialogHeader>

          <div className="py-3">
            <Label>Target Canonical Skill</Label>
            <Select value={mergeTargetId} onValueChange={setMergeTargetId}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Select target skill" />
              </SelectTrigger>
              <SelectContent>
                {taxonomy
                  .filter((s) => s.id !== mergingSkill?.id && s.status === "active")
                  .map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.display_name} ({s.category})
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setMergingSkill(null)}>
              Cancel
            </Button>
            <Button disabled={!mergeTargetId || isMerging} onClick={handleMergeSkills}>
              Confirm Merge
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
