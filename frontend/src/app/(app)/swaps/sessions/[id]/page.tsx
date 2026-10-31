"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Video,
  MapPin,
  Download,
  CheckCircle2,
  AlertTriangle,
  Send,
  MessageSquare,
  ShieldCheck,
  Star,
  ExternalLink,
  ChevronLeft,
  Sparkles,
  Award,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiClient, getAccessToken } from "@/lib/api-client";
import { swapApi } from "@/lib/swap-api";
import {
  SwapSession,
  SwapMessage,
  SwapReview,
  SwapReviewCreate,
  SwapDisputeCreate,
} from "@/types/swap";
import { useToast } from "@/components/ui/use-toast";

const ACCOMPLISHMENT_TAGS = [
  "Patient Teacher",
  "Clear Explanations",
  "Well Prepared",
  "Great Listener",
  "Practical Exercises",
  "Encouraging",
  "Punctual",
  "Engaging Discussion",
];

export default function SwapSessionRoomPage() {
  const params = useParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const sessionId = params.id as string;

  const [chatInput, setChatInput] = React.useState("");
  const chatScrollRef = React.useRef<HTMLDivElement>(null);

  // Dispute Modal State
  const [isDisputeOpen, setIsDisputeOpen] = React.useState(false);
  const [disputeReason, setDisputeReason] = React.useState("");

  // Review Modal State
  const [isReviewOpen, setIsReviewOpen] = React.useState(false);
  const [rating, setRating] = React.useState(5);
  const [selectedTags, setSelectedTags] = React.useState<string[]>([]);
  const [publicComment, setPublicComment] = React.useState("");
  const [privateFeedback, setPrivateFeedback] = React.useState("");

  // Current Viewer
  const { data: currentUser } = useQuery({
    queryKey: ["current-user"],
    queryFn: async () => {
      return await apiClient.get<{ id: string; username: string; display_name: string }>("/users/me");
    },
  });

  // Fetch Session
  const { data: session, isLoading, error } = useQuery<SwapSession>({
    queryKey: ["swap-session", sessionId],
    queryFn: async () => {
      return await swapApi.getSessionById(sessionId);
    },
    refetchInterval: 5000, // Real-time poll for status updates
  });

  // Fetch Messages
  const { data: messages } = useQuery<SwapMessage[]>({
    queryKey: ["swap-messages", sessionId],
    queryFn: async () => {
      return await swapApi.getSessionMessages(sessionId);
    },
    refetchInterval: 3000, // Real-time chat polling
  });

  // Fetch Reviews
  const { data: reviews } = useQuery<SwapReview[]>({
    queryKey: ["swap-reviews", sessionId],
    queryFn: async () => {
      return await swapApi.getSessionReviews(sessionId);
    },
  });

  // Auto-scroll chat
  React.useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Send Message Mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      return await swapApi.postSessionMessage(sessionId, content);
    },
    onSuccess: () => {
      setChatInput("");
      queryClient.invalidateQueries({ queryKey: ["swap-messages", sessionId] });
    },
  });

  // Confirm Completion Mutation
  const confirmMutation = useMutation({
    mutationFn: async () => {
      return await swapApi.confirmSession(sessionId);
    },
    onSuccess: (updated) => {
      toast({
        title: "Session Confirmed",
        description:
          updated.status === "completed"
            ? "Both parties confirmed! The session is officially completed."
            : "Your confirmation was recorded. Waiting for your partner to confirm.",
      });
      queryClient.invalidateQueries({ queryKey: ["swap-session", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["swap-sessions"] });
      if (updated.status === "completed") {
        setIsReviewOpen(true);
      }
    },
  });

  // Dispute Mutation
  const disputeMutation = useMutation({
    mutationFn: async (data: SwapDisputeCreate) => {
      return await swapApi.disputeSession(sessionId, data);
    },
    onSuccess: () => {
      toast({
        variant: "destructive",
        title: "Dispute Filed",
        description: "Your report was submitted to admins for review.",
      });
      setIsDisputeOpen(false);
      queryClient.invalidateQueries({ queryKey: ["swap-session", sessionId] });
    },
  });

  // Submit Review Mutation
  const reviewMutation = useMutation({
    mutationFn: async (data: SwapReviewCreate) => {
      return await swapApi.submitSessionReview(sessionId, data);
    },
    onSuccess: (savedReview) => {
      toast({
        title: "Review Submitted!",
        description: savedReview.is_revealed
          ? "Mutual reviews revealed! Thank you for exchanging skills."
          : "Double-blind review recorded! It will reveal once your partner submits theirs.",
      });
      setIsReviewOpen(false);
      queryClient.invalidateQueries({ queryKey: ["swap-reviews", sessionId] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to submit review.";
      toast({
        variant: "destructive",
        title: "Error",
        description: msg,
      });
    },
  });

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || sendMessageMutation.isPending) return;
    sendMessageMutation.mutate(chatInput.trim());
  };

  const handleDownloadIcs = async () => {
    try {
      const res = await fetch(`/api/v1/swaps/sessions/${sessionId}/ics`, {
        headers: {
          Authorization: `Bearer ${getAccessToken() || ""}`,
        },
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `nexus-swap-${sessionId}.ics`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (e) {
      console.error("Failed to download .ics", e);
    }
  };

  const toggleTag = (tag: string) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter((t) => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  if (isLoading) {
    return (
      <div className="container max-w-5xl py-12 text-center text-sm text-muted-foreground">
        Loading swap session room...
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="container max-w-5xl py-12 text-center space-y-3">
        <p className="text-destructive font-semibold">Session not found or unauthorized.</p>
        <Link href="/swaps/sessions">
          <Button variant="outline" size="sm">
            Back to Sessions
          </Button>
        </Link>
      </div>
    );
  }

  const halves = session.halves || [];
  const firstHalf = halves.find((h) => h.half_number === 1);
  const secondHalf = halves.find((h) => h.half_number === 2);

  const isUserA = currentUser?.id === session.user_a.id;
  const partner = isUserA ? session.user_b : session.user_a;
  const userConfirmed = isUserA ? session.user_a_confirmed : session.user_b_confirmed;

  const hasReviewed = reviews?.some((r) => r.reviewer.id === currentUser?.id);
  const bothRevealed = reviews?.some((r) => r.is_revealed);

  return (
    <div className="container max-w-6xl py-4 space-y-5">
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3">
        <div className="flex items-center gap-2">
          <Link href="/swaps/sessions">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ChevronLeft className="w-4 h-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold">Skill Swap Session Room</h1>
              <Badge variant="outline" className="text-xs">
                {session.mode === "video" ? "Jitsi Meet Video" : "In-Person Meetup"}
              </Badge>
              {session.status === "completed" && (
                <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-300">
                  Completed
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Peer exchange with <strong>@{partner.username}</strong> ({partner.display_name})
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8 text-xs gap-1.5" onClick={handleDownloadIcs}>
            <Download className="w-3.5 h-3.5" />
            .ics
          </Button>

          {session.status !== "completed" && (
            <Button
              size="sm"
              variant={userConfirmed ? "outline" : "default"}
              className="h-8 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => confirmMutation.mutate()}
              disabled={confirmMutation.isPending || userConfirmed}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {userConfirmed ? "You Confirmed ✓" : "Confirm Completed"}
            </Button>
          )}

          {session.status === "completed" && !hasReviewed && (
            <Button
              size="sm"
              className="h-8 text-xs gap-1.5 bg-amber-500 hover:bg-amber-600 text-white font-medium"
              onClick={() => setIsReviewOpen(true)}
            >
              <Star className="w-3.5 h-3.5 fill-current" />
              Leave Blind Review
            </Button>
          )}

          {session.status !== "completed" && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs text-muted-foreground hover:text-destructive"
              onClick={() => setIsDisputeOpen(true)}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Dispute
            </Button>
          )}
        </div>
      </div>

      {/* Split-Halves Timeline Header */}
      <Card className="border bg-gradient-to-r from-muted/50 to-muted/20">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Half 1 */}
            <div className="p-3 bg-background rounded-lg border space-y-1 relative">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-primary flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center text-[10px]">
                    1
                  </span>
                  Half 1 (30 Minutes)
                </span>
                <span className="text-muted-foreground text-[11px]">
                  {firstHalf && new Date(firstHalf.start_time_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} &ndash;{" "}
                  {firstHalf && new Date(firstHalf.end_time_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              <p className="text-sm font-semibold pl-6">
                {firstHalf?.mentor.display_name} teaches {firstHalf?.learner.display_name}
              </p>
              <p className="text-xs text-muted-foreground pl-6">
                Topic: <strong className="text-foreground">{firstHalf?.skill.display_name}</strong>
              </p>
            </div>

            {/* Half 2 */}
            <div className="p-3 bg-background rounded-lg border space-y-1 relative">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-indigo-500/20 flex items-center justify-center text-[10px]">
                    2
                  </span>
                  Half 2 (30 Minutes)
                </span>
                <span className="text-muted-foreground text-[11px]">
                  {secondHalf && new Date(secondHalf.start_time_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} &ndash;{" "}
                  {secondHalf && new Date(secondHalf.end_time_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              <p className="text-sm font-semibold pl-6">
                {secondHalf?.mentor.display_name} teaches {secondHalf?.learner.display_name}
              </p>
              <p className="text-xs text-muted-foreground pl-6">
                Topic: <strong className="text-foreground">{secondHalf?.skill.display_name}</strong>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Grid: Interactive Room + Logistics Chat */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left 2 Cols: Video / Location Display */}
        <div className="lg:col-span-2 space-y-4">
          {session.mode === "video" ? (
            <Card className="overflow-hidden border">
              <div className="bg-slate-900 text-white p-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Video className="w-4 h-4 text-emerald-400" />
                  <span className="font-semibold">Live Video Room (Jitsi Meet)</span>
                </div>
                {session.jitsi_room_url && (
                  <a
                    href={session.jitsi_room_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[11px] text-slate-300 hover:text-white"
                  >
                    <span>Open in New Window</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>

              {session.jitsi_room_url ? (
                <div className="w-full aspect-video bg-black relative">
                  <iframe
                    src={`${session.jitsi_room_url}#config.prejoinPageEnabled=false&userInfo.displayName=${encodeURIComponent(
                      currentUser?.display_name || "User"
                    )}`}
                    allow="camera; microphone; fullscreen; display-capture"
                    className="w-full h-full border-0"
                    title="Nexus Skill Swap Jitsi Meet Room"
                  />
                </div>
              ) : (
                <div className="aspect-video flex items-center justify-center bg-muted/40 text-muted-foreground text-xs">
                  Video room token pending generation.
                </div>
              )}
            </Card>
          ) : (
            <Card className="border">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-emerald-600" />
                  In-Person Public Meetup Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-muted/40 rounded-lg space-y-2 border">
                  <div>
                    <Label className="text-xs text-muted-foreground font-semibold">Public Venue:</Label>
                    <p className="text-base font-bold text-foreground">
                      {session.public_place_name || "Campus Community Library"}
                    </p>
                  </div>
                  {session.public_place_address && (
                    <div>
                      <Label className="text-xs text-muted-foreground font-semibold">Address / Landmark:</Label>
                      <p className="text-xs text-muted-foreground">{session.public_place_address}</p>
                    </div>
                  )}
                </div>

                <div className="p-4 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900 rounded-lg space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                    <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    Public Venue Safety Checklist
                  </div>
                  <ul className="text-[11px] text-emerald-700 dark:text-emerald-400 space-y-1 list-disc pl-4">
                    <li>Always meet in an open, public area during daylight or well-lit hours.</li>
                    <li>Verify your swap partner&apos;s Student USN or College ID upon arrival.</li>
                    <li>Never invite or accept an invitation to a private residence or secluded location.</li>
                    <li>Use the logistics chat on this page to let your partner know when you&apos;ve arrived.</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Mutual Reviews Display (when revealed) */}
          {bothRevealed && (
            <Card className="border border-emerald-500/40 bg-emerald-50/20 dark:bg-emerald-950/10">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                  <Award className="w-4 h-4" />
                  Mutual Double-Blind Reviews Revealed
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 pt-0">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {reviews?.map((r) => (
                    <div key={r.id} className="p-3 bg-background rounded-lg border space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs">From @{r.reviewer.username}:</span>
                        <div className="flex items-center gap-0.5 text-amber-500">
                          {Array.from({ length: r.rating || 5 }).map((_, i) => (
                            <Star key={i} className="w-3.5 h-3.5 fill-current" />
                          ))}
                        </div>
                      </div>
                      <p className="text-muted-foreground italic">&ldquo;{r.public_comment || "Great swap!"}&rdquo;</p>
                      {r.tags && r.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {r.tags.map((t, idx) => (
                            <Badge key={idx} variant="secondary" className="text-[10px] py-0">
                              {t}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Col: Logistics Chat Sidebar */}
        <div className="space-y-4">
          <Card className="border flex flex-col h-[520px]">
            <CardHeader className="p-3.5 border-b bg-muted/20">
              <CardTitle className="text-xs font-semibold flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-primary" />
                Session Logistics Chat
              </CardTitle>
            </CardHeader>

            {/* Chat Messages */}
            <div ref={chatScrollRef} className="flex-1 p-3 overflow-y-auto space-y-3 text-xs">
              {messages && messages.length > 0 ? (
                messages.map((msg) => {
                  const isMe = msg.sender.id === currentUser?.id;
                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${isMe ? "items-end" : "items-start"}`}
                    >
                      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground mb-0.5">
                        <span className="font-semibold">{isMe ? "You" : `@${msg.sender.username}`}</span>
                        <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                      <div
                        className={`p-2.5 rounded-lg max-w-[85%] break-words ${
                          isMe
                            ? "bg-primary text-primary-foreground rounded-br-none"
                            : "bg-muted text-foreground rounded-bl-none"
                        }`}
                      >
                        {msg.content}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-16 text-muted-foreground space-y-1">
                  <p className="font-medium text-xs">No coordination messages yet</p>
                  <p className="text-[11px]">Say hi and coordinate your swap logistics!</p>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <form onSubmit={handleSendMessage} className="p-2.5 border-t bg-muted/10 flex gap-2">
              <Input
                placeholder="Type logistics message..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                maxLength={500}
                className="h-8 text-xs"
              />
              <Button type="submit" size="sm" className="h-8 px-3" disabled={!chatInput.trim() || sendMessageMutation.isPending}>
                <Send className="w-3.5 h-3.5" />
              </Button>
            </form>
          </Card>
        </div>
      </div>

      {/* Double-Blind Review Modal */}
      <Dialog open={isReviewOpen} onOpenChange={setIsReviewOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" />
              Double-Blind Peer Review
            </DialogTitle>
            <DialogDescription>
              Rate your mentorship swap with @{partner.username}.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <Alert className="py-2.5 bg-amber-500/10 border-amber-500/20 text-xs">
              <ShieldCheck className="w-4 h-4 text-amber-600" />
              <AlertDescription className="text-amber-900 dark:text-amber-200 text-[11px]">
                <strong>Privacy Isolated:</strong> Your rating and comments will remain strictly
                hidden until @{partner.username} also submits their review, or 7 days elapse.
              </AlertDescription>
            </Alert>

            {/* Star Rating */}
            <div className="space-y-1 text-center">
              <Label className="text-xs font-semibold">Overall Experience</Label>
              <div className="flex items-center justify-center gap-1.5 pt-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    className="p-1 hover:scale-110 transition-transform"
                  >
                    <Star
                      className={`w-7 h-7 ${
                        star <= rating
                          ? "text-amber-500 fill-amber-500"
                          : "text-muted-foreground/30"
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Accomplishment Tags */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Accomplishments & Strengths</Label>
              <div className="flex flex-wrap gap-1.5">
                {ACCOMPLISHMENT_TAGS.map((tag) => {
                  const isSelected = selectedTags.includes(tag);
                  return (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => toggleTag(tag)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
                        isSelected
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-muted/40 border-border text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Public Review */}
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Public Review Comment</Label>
              <Textarea
                placeholder="Share constructive praise about how your peer taught or engaged..."
                value={publicComment}
                onChange={(e) => setPublicComment(e.target.value)}
                rows={2}
                maxLength={500}
                className="text-xs resize-none"
              />
            </div>

            {/* Private Mentor Feedback */}
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Private Feedback (Only visible to partner)</Label>
              <Textarea
                placeholder="Optional private tips or suggestions for next time..."
                value={privateFeedback}
                onChange={(e) => setPrivateFeedback(e.target.value)}
                rows={2}
                maxLength={500}
                className="text-xs resize-none"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setIsReviewOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              className="bg-amber-500 hover:bg-amber-600 text-white font-medium"
              disabled={reviewMutation.isPending}
              onClick={() =>
                reviewMutation.mutate({
                  rating,
                  tags: selectedTags,
                  public_comment: publicComment,
                  private_feedback: privateFeedback,
                })
              }
            >
              {reviewMutation.isPending ? "Submitting..." : "Submit Blind Review"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dispute Modal */}
      <Dialog open={isDisputeOpen} onOpenChange={setIsDisputeOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="w-5 h-5" />
              Report Dispute or No-Show
            </DialogTitle>
            <DialogDescription>
              Report a missed session, inappropriate conduct, or safety issue to platform moderators.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <Label className="text-xs font-semibold">Explain what occurred *</Label>
            <Textarea
              placeholder="Provide specific details (e.g. partner did not show up, payment was requested, etc.)..."
              value={disputeReason}
              onChange={(e) => setDisputeReason(e.target.value)}
              rows={4}
              maxLength={1000}
              className="text-xs resize-none"
              required
            />
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setIsDisputeOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={disputeReason.length < 10 || disputeMutation.isPending}
              onClick={() => disputeMutation.mutate({ reason: disputeReason })}
            >
              {disputeMutation.isPending ? "Submitting..." : "Submit Report"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
