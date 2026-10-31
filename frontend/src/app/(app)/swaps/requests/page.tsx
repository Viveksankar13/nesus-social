"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Inbox,
  Video,
  MapPin,
  CheckCircle,
  XCircle,
  RotateCcw,
  Ban,
  ArrowRight,
  MessageSquare,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { SwapNav } from "@/components/swaps/swap-nav";
import { SlotPicker } from "@/components/swaps/slot-picker";
import { swapApi } from "@/lib/swap-api";
import {
  SwapRequest,
  SwapRequestListResponse,
  SwapRequestAccept,
  SwapRequestCounter,
  ProposedSlot,
} from "@/types/swap";
import { useToast } from "@/components/ui/use-toast";

export default function SwapRequestsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = React.useState<"incoming" | "outgoing">("incoming");

  // Accept Dialog State
  const [acceptingReq, setAcceptingReq] = React.useState<SwapRequest | null>(null);
  const [selectedSlotIdx, setSelectedSlotIdx] = React.useState(0);

  // Counter Dialog State
  const [counteringReq, setCounteringReq] = React.useState<SwapRequest | null>(null);
  const [counterNote, setCounterNote] = React.useState("");
  const [counterSlots, setCounterSlots] = React.useState<ProposedSlot[]>([]);

  // Fetch Requests
  const { data, isLoading } = useQuery<SwapRequestListResponse>({
    queryKey: ["swap-requests"],
    queryFn: async () => {
      return await swapApi.getRequests();
    },
  });

  // Accept Mutation
  const acceptMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: SwapRequestAccept;
    }) => {
      return await swapApi.acceptRequest(id, payload);
    },
    onSuccess: () => {
      toast({
        title: "Swap Accepted!",
        description: "Your session has been scheduled into two 30-minute halves.",
      });
      queryClient.invalidateQueries({ queryKey: ["swap-requests"] });
      queryClient.invalidateQueries({ queryKey: ["swap-sessions"] });
      setAcceptingReq(null);
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Could not accept proposal.";
      toast({
        variant: "destructive",
        title: "Failed to accept",
        description: msg,
      });
    },
  });

  // Decline Mutation
  const declineMutation = useMutation({
    mutationFn: async (id: string) => {
      return await swapApi.declineRequest(id);
    },
    onSuccess: () => {
      toast({ title: "Proposal Declined" });
      queryClient.invalidateQueries({ queryKey: ["swap-requests"] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to decline.";
      toast({
        variant: "destructive",
        title: "Error",
        description: msg,
      });
    },
  });

  // Counter Mutation
  const counterMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: SwapRequestCounter;
    }) => {
      return await swapApi.counterRequest(id, payload);
    },
    onSuccess: () => {
      toast({
        title: "Counter-Proposal Sent",
        description: "Your partner will be notified of your proposed alternative times.",
      });
      queryClient.invalidateQueries({ queryKey: ["swap-requests"] });
      setCounteringReq(null);
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to counter.";
      toast({
        variant: "destructive",
        title: "Error",
        description: msg,
      });
    },
  });

  // Cancel Mutation
  const cancelMutation = useMutation({
    mutationFn: async (id: string) => {
      return await swapApi.cancelRequest(id);
    },
    onSuccess: () => {
      toast({ title: "Proposal Cancelled" });
      queryClient.invalidateQueries({ queryKey: ["swap-requests"] });
    },
  });

  const incomingRequests = data?.incoming || [];
  const outgoingRequests = data?.outgoing || [];
  const activeIncomingCount = incomingRequests.filter((r) => r.status === "pending" || r.status === "countered").length;

  const renderStatusBadge = (status: SwapRequest["status"]) => {
    switch (status) {
      case "pending":
        return <Badge className="bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-300">Pending Response</Badge>;
      case "countered":
        return <Badge className="bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-300">Counter-Offered</Badge>;
      case "accepted":
        return <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-300">Accepted & Scheduled</Badge>;
      case "declined":
        return <Badge variant="secondary">Declined</Badge>;
      case "cancelled":
        return <Badge variant="outline" className="text-muted-foreground">Cancelled</Badge>;
      case "expired":
        return <Badge variant="destructive">Expired (72h)</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const renderProposalCard = (req: SwapRequest, isIncoming: boolean) => {
    const partner = isIncoming ? req.requester : req.recipient;
    const canRespond = isIncoming && (req.status === "pending" || req.status === "countered");
    const canCancel = !isIncoming && (req.status === "pending" || req.status === "countered");

    return (
      <Card key={req.id} className="overflow-hidden border hover:border-primary/40 transition-colors">
        <CardContent className="p-5 space-y-4">
          {/* Header Row */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Avatar className="w-10 h-10 border">
                <AvatarImage src={partner.avatar_url || ""} />
                <AvatarFallback>{partner.display_name.slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">{partner.display_name}</span>
                  <span className="text-xs text-muted-foreground">@{partner.username}</span>
                  {partner.usn && (
                    <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-mono">
                      USN: {partner.usn}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                  <span>{isIncoming ? "Proposed to you" : "Proposed by you"}</span>
                  <span>&bull;</span>
                  <span>{new Date(req.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto">
              <Badge variant="outline" className="gap-1 text-xs">
                {req.mode === "video" ? <Video className="w-3 h-3 text-primary" /> : <MapPin className="w-3 h-3 text-emerald-600" />}
                {req.mode === "video" ? "Video Meet" : "In-Person"}
              </Badge>
              {renderStatusBadge(req.status)}
            </div>
          </div>

          {/* Skills Exchange Matrix */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-muted/40 rounded-lg text-xs">
            <div className="space-y-1">
              <span className="text-muted-foreground font-semibold">
                {isIncoming ? "Peer Teaches You (30m):" : "You Teach Peer (30m):"}
              </span>
              <p className="font-bold text-foreground text-sm flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                {req.offered_skill.display_name}
              </p>
            </div>
            <div className="space-y-1 sm:border-l sm:pl-3">
              <span className="text-muted-foreground font-semibold">
                {isIncoming ? "You Teach Peer (30m):" : "Peer Teaches You (30m):"}
              </span>
              <p className="font-bold text-foreground text-sm flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block" />
                {req.wanted_skill.display_name}
              </p>
            </div>
          </div>

          {/* Proposal Message */}
          <div className="text-xs text-muted-foreground bg-background p-3 rounded-md border space-y-1">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-primary" />
              Introductory Message:
            </div>
            <p className="italic">&ldquo;{req.message}&rdquo;</p>
          </div>

          {/* Counter Note (if present) */}
          {req.counter_note && (
            <div className="text-xs text-purple-900 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/30 p-3 rounded-md border border-purple-200 dark:border-purple-800 space-y-1">
              <span className="font-semibold flex items-center gap-1.5">
                <RotateCcw className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
                Counter-Offer Note:
              </span>
              <p className="italic">&ldquo;{req.counter_note}&rdquo;</p>
            </div>
          )}

          {/* Proposed Slots */}
          <div className="space-y-1.5">
            <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-primary" />
              Proposed 30-Minute Slots ({req.proposed_slots.length}):
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {req.proposed_slots.map((s, idx) => {
                const start = new Date(s.start_time_utc);
                const end = new Date(s.end_time_utc);
                return (
                  <div
                    key={idx}
                    className="flex items-center gap-2 p-2 rounded border bg-muted/20 text-xs"
                  >
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center text-[10px]">
                      {idx + 1}
                    </span>
                    <span>
                      {start.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })},{" "}
                      {start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} &ndash;{" "}
                      {end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t">
            {canRespond && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs gap-1.5 text-destructive hover:bg-destructive/10"
                  onClick={() => declineMutation.mutate(req.id)}
                  disabled={declineMutation.isPending}
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Decline
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs gap-1.5"
                  onClick={() => {
                    setCounteringReq(req);
                    setCounterNote("");
                    setCounterSlots(req.proposed_slots);
                  }}
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Counter-Offer
                </Button>

                <Button
                  size="sm"
                  className="h-8 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
                  onClick={() => {
                    setAcceptingReq(req);
                    setSelectedSlotIdx(0);
                  }}
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Accept & Schedule
                </Button>
              </>
            )}

            {canCancel && (
              <Button
                size="sm"
                variant="outline"
                className="h-8 text-xs gap-1.5 text-muted-foreground hover:text-destructive"
                onClick={() => cancelMutation.mutate(req.id)}
                disabled={cancelMutation.isPending}
              >
                <Ban className="w-3.5 h-3.5" />
                Cancel Proposal
              </Button>
            )}

            {req.status === "accepted" && (
              <Link href="/swaps/sessions">
                <Button size="sm" className="h-8 text-xs gap-1.5">
                  <span>Enter Session Room</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="container max-w-5xl py-6 space-y-6">
      <SwapNav incomingCount={activeIncomingCount} />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Proposals Inbox</h1>
          <p className="text-sm text-muted-foreground">
            Manage incoming skill exchange invitations and track outgoing proposals.
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "incoming" | "outgoing")} className="w-full">
        <TabsList className="grid w-full sm:w-[400px] grid-cols-2">
          <TabsTrigger value="incoming" className="gap-2">
            <span>Incoming Proposals</span>
            {activeIncomingCount > 0 && (
              <Badge className="h-5 px-1.5 text-[10px] bg-amber-500 text-white">
                {activeIncomingCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="outgoing">
            Outgoing Proposals ({outgoingRequests.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="incoming" className="space-y-4 pt-4">
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground text-sm">
              Loading proposals...
            </div>
          ) : incomingRequests.length === 0 ? (
            <div className="text-center py-16 border rounded-xl bg-muted/20 space-y-3">
              <Inbox className="w-10 h-10 text-muted-foreground mx-auto opacity-50" />
              <p className="text-sm font-semibold text-muted-foreground">No incoming proposals yet</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Publish a Swap Offer listing in the Discovery Hub to invite peers to exchange skills with you!
              </p>
            </div>
          ) : (
            incomingRequests.map((req) => renderProposalCard(req, true))
          )}
        </TabsContent>

        <TabsContent value="outgoing" className="space-y-4 pt-4">
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground text-sm">
              Loading proposals...
            </div>
          ) : outgoingRequests.length === 0 ? (
            <div className="text-center py-16 border rounded-xl bg-muted/20 space-y-3">
              <Inbox className="w-10 h-10 text-muted-foreground mx-auto opacity-50" />
              <p className="text-sm font-semibold text-muted-foreground">No outgoing proposals</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Explore the Discovery Hub and propose a 30-minute peer swap with students nearby.
              </p>
              <Link href="/swaps">
                <Button size="sm" variant="outline" className="mt-2 text-xs">
                  Browse Listings
                </Button>
              </Link>
            </div>
          ) : (
            outgoingRequests.map((req) => renderProposalCard(req, false))
          )}
        </TabsContent>
      </Tabs>

      {/* Accept Proposal Dialog */}
      {acceptingReq && (
        <Dialog open={true} onOpenChange={() => setAcceptingReq(null)}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
                Accept & Confirm Swap
              </DialogTitle>
              <DialogDescription>
                Select which proposed 30-minute time slot you would like to lock into the calendar.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <Label className="text-xs font-semibold">Choose Meeting Time:</Label>
              <div className="space-y-2">
                {acceptingReq.proposed_slots.map((s, idx) => {
                  const start = new Date(s.start_time_utc);
                  const end = new Date(s.end_time_utc);
                  const isSelected = selectedSlotIdx === idx;
                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedSlotIdx(idx)}
                      className={`p-3 rounded-lg border text-xs cursor-pointer transition-all flex items-center justify-between ${
                        isSelected
                          ? "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20 font-semibold text-emerald-900 dark:text-emerald-300"
                          : "border-border hover:bg-muted"
                      }`}
                    >
                      <span>
                        Slot {idx + 1}: {start.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })},{" "}
                        {start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} &ndash;{" "}
                        {end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      {isSelected && <CheckCircle className="w-4 h-4 text-emerald-600" />}
                    </div>
                  );
                })}
              </div>

              <div className="p-3 bg-muted/40 rounded-lg text-[11px] text-muted-foreground space-y-1">
                <p>&bull; <strong>Format:</strong> Two consecutive 30-minute halves (60m total).</p>
                <p>&bull; <strong>Half 1:</strong> Peer teaches you {acceptingReq.offered_skill.display_name} (30m).</p>
                <p>&bull; <strong>Half 2:</strong> You teach peer {acceptingReq.wanted_skill.display_name} (30m).</p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" size="sm" onClick={() => setAcceptingReq(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                disabled={acceptMutation.isPending}
                onClick={() =>
                  acceptMutation.mutate({
                    id: acceptingReq.id,
                    payload: { selected_slot_index: selectedSlotIdx },
                  })
                }
              >
                {acceptMutation.isPending ? "Scheduling..." : "Confirm & Schedule"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Counter Proposal Dialog */}
      {counteringReq && (
        <Dialog open={true} onOpenChange={() => setCounteringReq(null)}>
          <DialogContent className="max-w-xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <RotateCcw className="w-5 h-5 text-purple-600" />
                Counter-Propose Alternative Times
              </DialogTitle>
              <DialogDescription>
                Propose up to 3 alternative 30-minute slots that fit your availability better.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <SlotPicker
                slots={counterSlots}
                onChange={(newSlots) => setCounterSlots(newSlots)}
                maxSlots={3}
              />

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Note to Partner *</Label>
                <Textarea
                  placeholder="Explain why these times work better for you..."
                  value={counterNote}
                  onChange={(e) => setCounterNote(e.target.value)}
                  rows={2}
                  className="text-xs resize-none"
                  required
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" size="sm" onClick={() => setCounteringReq(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="bg-purple-600 hover:bg-purple-700 text-white"
                disabled={counterMutation.isPending || counterNote.length < 5 || counterSlots.length === 0}
                onClick={() =>
                  counterMutation.mutate({
                    id: counteringReq.id,
                    payload: {
                      message: counterNote,
                      proposed_slots: counterSlots,
                    },
                  })
                }
              >
                {counterMutation.isPending ? "Sending..." : "Submit Counter-Offer"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
