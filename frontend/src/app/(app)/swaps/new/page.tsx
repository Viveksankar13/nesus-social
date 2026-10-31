"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  GraduationCap,
  Loader2,
  MapPin,
  Plus,
  Repeat,
  ShieldCheck,
  Sparkles,
  Video,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { swapApi } from "@/lib/swap-api";
import { SwapListingCreate } from "@/types/swap";

export default function CreateSwapOfferPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [selectedOfferedId, setSelectedOfferedId] = useState<string>("");
  const [selectedWantedId, setSelectedWantedId] = useState<string>("open");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [modes, setModes] = useState<string[]>(["video"]);
  const [areaLabel, setAreaLabel] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [aiNotes, setAiNotes] = useState("");
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch taxonomy and user profile
  const { data: taxonomy = [] } = useQuery({
    queryKey: ["swap-taxonomy"],
    queryFn: swapApi.getTaxonomy,
  });

  useQuery({
    queryKey: ["swap-profile", "me"],
    queryFn: async () => {
      const p = await swapApi.getMyProfile();
      if (p.area_label && !areaLabel) {
        setAreaLabel(p.area_label);
      }
      return p;
    },
  });

  // Flatten skills
  const allSkills = React.useMemo(() => {
    return taxonomy.flatMap((group) => group.skills);
  }, [taxonomy]);

  // AI Draft Generator Mutation
  const handleGenerateAiDraft = async () => {
    if (!selectedOfferedId) {
      toast({
        title: "Please choose a skill first",
        description: "Select the skill you can teach before requesting an AI draft.",
        variant: "destructive",
      });
      return;
    }

    const offeredSkill = allSkills.find((s) => s.id === selectedOfferedId);
    const wantedSkill = allSkills.find((s) => s.id === selectedWantedId);

    setIsAiLoading(true);
    try {
      const res = await swapApi.generateAIDraft({
        skill_offered_name: offeredSkill?.display_name || "Technical Skill",
        skill_wanted_name: wantedSkill?.display_name,
        notes: aiNotes || undefined,
      });

      setTitle(res.title);
      setDescription(res.description);
      if (res.suggested_tags?.length) {
        setTagsInput(res.suggested_tags.join(", "));
      }
      toast({
        title: "AI Draft Ready!",
        description: "Gemini generated a listing draft. Feel free to refine it below.",
      });
    } catch {
      toast({
        title: "Draft generation error",
        description: "Could not generate AI draft. You can write your description manually.",
        variant: "destructive",
      });
    } finally {
      setIsAiLoading(false);
    }
  };

  // Create Listing Mutation
  const createMutation = useMutation({
    mutationFn: async (payload: SwapListingCreate) => {
      return swapApi.createListing(payload);
    },
    onSuccess: (data) => {
      toast({
        title: "Swap Offer Created!",
        description: "Your listing is now live in the Hyper-Local Skill Swap Discovery.",
      });
      router.push(`/swaps/${data.id}`);
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      const detail = err.response?.data?.detail || err.message || "Failed to create swap offer.";
      setErrorMessage(detail);
      toast({
        title: "Could not create offer",
        description: detail,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!selectedOfferedId) {
      setErrorMessage("Please select a skill you can teach.");
      return;
    }
    if (!title.trim() || title.trim().length < 3) {
      setErrorMessage("Title must be at least 3 characters long.");
      return;
    }
    if (!description.trim() || description.trim().length < 10) {
      setErrorMessage("Description must be at least 10 characters long.");
      return;
    }
    if (modes.length === 0) {
      setErrorMessage("Please select at least one exchange mode (Video or In-person).");
      return;
    }

    const tags = tagsInput
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter((t) => t.length > 0);

    createMutation.mutate({
      title: title.trim(),
      skill_offered_id: selectedOfferedId,
      skill_wanted_id: selectedWantedId !== "open" ? selectedWantedId : null,
      description: description.trim(),
      modes,
      area_label: areaLabel.trim() || null,
      tags,
    });
  };

  const toggleMode = (m: string) => {
    setModes((prev) =>
      prev.includes(m) ? prev.filter((item) => item !== m) : [...prev, m]
    );
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Link href="/swaps" className="hover:text-foreground flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Swaps Discovery</span>
        </Link>
      </div>

      <div className="space-y-2">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight flex items-center gap-2.5">
          <Repeat className="w-6 h-6 text-indigo-500" />
          <span>Create a 30-Minute Swap Offer</span>
        </h1>
        <p className="text-sm text-muted-foreground">
          Offer your peer mentorship in exchange for learning something new. 100% reciprocal, non-monetary, and safe.
        </p>
      </div>

      {/* Strict Non-Monetary Policy Warning */}
      <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-xs flex items-start gap-2.5 text-emerald-800 dark:text-emerald-300">
        <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600 dark:text-emerald-400" />
        <div>
          <span className="font-semibold block">Strictly Non-Monetary Peer Exchange</span>
          <span>
            Nexus Swaps are barter-only (30-minute peer help for 30-minute peer help). Mentions of cash, hourly rates, or payment solicitation are prohibited and filtered.
          </span>
        </div>
      </div>

      {errorMessage && (
        <Alert variant="destructive" className="rounded-xl">
          <AlertCircle className="w-4 h-4" />
          <AlertTitle>Validation Error</AlertTitle>
          <AlertDescription className="text-xs">{errorMessage}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card className="rounded-2xl border-border shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-semibold">1. Choose Skills to Swap</CardTitle>
            <CardDescription className="text-xs">
              Select what you are offering to teach and what you want in return.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs font-semibold flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                  <GraduationCap className="w-4 h-4" />
                  <span>Skill I Can Teach (Offered) *</span>
                </Label>
                <Select
                  value={selectedOfferedId}
                  onValueChange={(val) => setSelectedOfferedId(val)}
                >
                  <SelectTrigger className="h-10 text-xs rounded-xl">
                    <SelectValue placeholder="Select offered skill" />
                  </SelectTrigger>
                  <SelectContent className="max-h-60">
                    {taxonomy.map((group) => (
                      <React.Fragment key={group.category}>
                        <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-muted/40">
                          {group.category}
                        </div>
                        {group.skills.map((skill) => (
                          <SelectItem key={skill.id} value={skill.id} className="text-xs">
                            {skill.display_name}
                          </SelectItem>
                        ))}
                      </React.Fragment>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-semibold flex items-center gap-1.5 text-indigo-600 dark:text-indigo-400">
                  <BookOpen className="w-4 h-4" />
                  <span>Skill I Want in Return</span>
                </Label>
                <Select
                  value={selectedWantedId}
                  onValueChange={(val) => setSelectedWantedId(val)}
                >
                  <SelectTrigger className="h-10 text-xs rounded-xl">
                    <SelectValue placeholder="Open to anything / Pay it forward" />
                  </SelectTrigger>
                  <SelectContent className="max-h-60">
                    <SelectItem value="open" className="text-xs font-medium text-primary">
                      ✨ Open to anything / Pay it forward
                    </SelectItem>
                    {taxonomy.map((group) => (
                      <React.Fragment key={group.category}>
                        <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-muted/40">
                          {group.category}
                        </div>
                        {group.skills.map((skill) => (
                          <SelectItem key={skill.id} value={skill.id} className="text-xs">
                            {skill.display_name}
                          </SelectItem>
                        ))}
                      </React.Fragment>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* AI Draft Helper Box */}
            <div className="rounded-xl border border-indigo-500/30 bg-gradient-to-r from-indigo-500/10 via-purple-500/5 to-transparent p-3.5 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                  <Sparkles className="w-4 h-4 text-indigo-500" />
                  <span>Gemini AI Draft Helper</span>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleGenerateAiDraft}
                  disabled={isAiLoading || !selectedOfferedId}
                  className="h-7 text-xs gap-1.5"
                >
                  {isAiLoading ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Sparkles className="w-3 h-3 text-indigo-500" />
                  )}
                  <span>Draft Title & Description</span>
                </Button>
              </div>
              <Input
                value={aiNotes}
                onChange={(e) => setAiNotes(e.target.value)}
                placeholder="Optional notes for AI (e.g. beginner friendly, focus on App router and hooks)..."
                className="h-8 text-xs bg-background/80"
              />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-semibold">2. Offer Details</CardTitle>
            <CardDescription className="text-xs">
              Describe what you will cover in your 30-minute peer session.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="text-xs font-semibold">Offer Title *</Label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Next.js 14 App Router Mentorship in exchange for Resume Review"
                className="h-10 rounded-xl text-xs sm:text-sm"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-semibold">Description *</Label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Explain what topics you will walk through, what peers should prepare, and your exchange style..."
                rows={4}
                className="rounded-xl text-xs sm:text-sm leading-relaxed"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs font-semibold">Modes Accepted *</Label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => toggleMode("video")}
                    className={`flex-1 p-2 rounded-xl border text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                      modes.includes("video")
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-muted/40 text-muted-foreground border-border hover:bg-muted"
                    }`}
                  >
                    <Video className="w-3.5 h-3.5" />
                    <span>Video (Jitsi)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleMode("in_person")}
                    className={`flex-1 p-2 rounded-xl border text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                      modes.includes("in_person")
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-muted/40 text-muted-foreground border-border hover:bg-muted"
                    }`}
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>In-Person</span>
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-semibold flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
                  <span>Public Area Label</span>
                </Label>
                <Input
                  value={areaLabel}
                  onChange={(e) => setAreaLabel(e.target.value)}
                  placeholder="e.g. University Campus, Downtown Tech Hub"
                  className="h-10 rounded-xl text-xs"
                />
                <span className="text-[10px] text-muted-foreground block">
                  Never enter private home addresses. Public areas only.
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-semibold">Tags (comma separated)</Label>
              <Input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="e.g. react, nextjs, resume, frontend"
                className="h-10 rounded-xl text-xs"
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button type="button" variant="ghost" asChild>
            <Link href="/swaps">Cancel</Link>
          </Button>
          <Button
            type="submit"
            disabled={createMutation.isPending}
            className="gap-2 shadow-sm font-semibold"
          >
            {createMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            <span>Publish Swap Offer</span>
          </Button>
        </div>
      </form>
    </div>
  );
}
