"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Video,
  MapPin,
  ShieldCheck,
  AlertCircle,
  Send,
  Sparkles,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SlotPicker } from "@/components/swaps/slot-picker";
import { swapApi } from "@/lib/swap-api";
import { ProposedSlot, SwapRequestCreate } from "@/types/swap";
import { useToast } from "@/components/ui/use-toast";

interface ProposeSwapModalProps {
  isOpen: boolean;
  onClose: () => void;
  listingId?: string | null;
  recipientId: string;
  recipientUsername: string;
  offeredSkillId: string;
  offeredSkillName: string;
  wantedSkillId: string;
  wantedSkillName: string;
  defaultMode?: "video" | "in_person";
}

export function ProposeSwapModal({
  isOpen,
  onClose,
  listingId,
  recipientId,
  recipientUsername,
  offeredSkillId,
  offeredSkillName,
  wantedSkillId,
  wantedSkillName,
  defaultMode = "video",
}: ProposeSwapModalProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [mode, setMode] = React.useState<"video" | "in_person">(defaultMode);
  const [message, setMessage] = React.useState("");
  const [publicPlaceName, setPublicPlaceName] = React.useState("");
  const [publicPlaceAddress, setPublicPlaceAddress] = React.useState("");
  const [proposedSlots, setProposedSlots] = React.useState<ProposedSlot[]>([]);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const proposeMutation = useMutation({
    mutationFn: async (payload: SwapRequestCreate) => {
      return await swapApi.createRequest(payload);
    },
    onSuccess: () => {
      toast({
        title: "Proposal Sent!",
        description: `Your swap proposal was sent to @${recipientUsername}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["swap-requests"] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to submit swap proposal.";
      setErrorMessage(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (proposedSlots.length === 0) {
      setErrorMessage("Please propose at least one 30-minute time slot.");
      return;
    }

    if (mode === "in_person" && (!publicPlaceName || publicPlaceName.trim().length < 3)) {
      setErrorMessage("Please enter a named public venue for in-person swaps.");
      return;
    }

    proposeMutation.mutate({
      listing_id: listingId || null,
      recipient_id: recipientId,
      offered_skill_id: offeredSkillId,
      wanted_skill_id: wantedSkillId,
      mode,
      message,
      proposed_slots: proposedSlots,
      public_place_name: mode === "in_person" ? publicPlaceName : null,
      public_place_address: mode === "in_person" ? publicPlaceAddress : null,
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-bold">
            <Sparkles className="w-5 h-5 text-primary" />
            Propose a Skill Swap
          </DialogTitle>
          <DialogDescription>
            Propose a 30-minute reciprocal mentorship exchange with @{recipientUsername}.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5 pt-2">
          {/* Skills Matrix Display */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-muted/30 border rounded-lg text-xs">
            <div className="space-y-1">
              <span className="text-muted-foreground font-semibold">You teach (30m):</span>
              <p className="font-bold text-foreground text-sm">{offeredSkillName}</p>
            </div>
            <div className="space-y-1 border-l pl-3">
              <span className="text-muted-foreground font-semibold">You learn (30m):</span>
              <p className="font-bold text-foreground text-sm">{wantedSkillName}</p>
            </div>
          </div>

          {/* Mode Selector */}
          <div className="space-y-2">
            <Label className="text-xs font-semibold">Exchange Mode</Label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setMode("video")}
                className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-xs font-medium transition-all ${
                  mode === "video"
                    ? "bg-primary/10 border-primary text-primary font-bold shadow-sm"
                    : "border-border text-muted-foreground hover:bg-muted"
                }`}
              >
                <Video className="w-4 h-4" />
                Remote Jitsi Video
              </button>

              <button
                type="button"
                onClick={() => setMode("in_person")}
                className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-xs font-medium transition-all ${
                  mode === "in_person"
                    ? "bg-primary/10 border-primary text-primary font-bold shadow-sm"
                    : "border-border text-muted-foreground hover:bg-muted"
                }`}
              >
                <MapPin className="w-4 h-4" />
                In-Person Meetup
              </button>
            </div>
          </div>

          {/* In-Person Public Venue Guidance */}
          {mode === "in_person" && (
            <div className="space-y-3 p-3.5 bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 rounded-lg">
              <div className="flex items-center gap-2 text-xs font-semibold text-amber-800 dark:text-amber-300">
                <ShieldCheck className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                Public Venue Safety Guarantee
              </div>
              <p className="text-[11px] text-amber-700/90 dark:text-amber-400/90">
                To safeguard student privacy and safety, meetups must occur in an open, public
                facility (campus library, coffee shop, student center). Residential and private
                addresses are strictly prohibited.
              </p>
              <div className="space-y-2">
                <div>
                  <Label className="text-xs">Public Venue Name *</Label>
                  <Input
                    placeholder="e.g. Central Campus Library - 2nd Floor Study Room"
                    value={publicPlaceName}
                    onChange={(e) => setPublicPlaceName(e.target.value)}
                    required
                    className="h-9 text-xs mt-1"
                  />
                </div>
                <div>
                  <Label className="text-xs">Approximate Address / Landmark (Optional)</Label>
                  <Input
                    placeholder="e.g. University Boulevard, North Quad"
                    value={publicPlaceAddress}
                    onChange={(e) => setPublicPlaceAddress(e.target.value)}
                    className="h-9 text-xs mt-1"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Slot Picker Component */}
          <SlotPicker
            slots={proposedSlots}
            onChange={(newSlots) => setProposedSlots(newSlots)}
            maxSlots={3}
          />

          {/* Message Textarea */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <Label className="text-xs font-semibold">Introductory Message *</Label>
              <span className="text-[10px] text-muted-foreground">{message.length}/500</span>
            </div>
            <Textarea
              placeholder="Introduce what you hope to cover during your 30 minutes together..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              maxLength={500}
              required
              className="text-xs resize-none"
            />
            <p className="text-[11px] text-muted-foreground">
              &bull; Nexus Swaps are strictly non-monetary. Never offer or request payment.
            </p>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <Alert variant="destructive" className="py-2 text-xs">
              <AlertCircle className="w-4 h-4" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={proposeMutation.isPending || message.length < 5}
              className="gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              {proposeMutation.isPending ? "Sending..." : "Submit Proposal"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
