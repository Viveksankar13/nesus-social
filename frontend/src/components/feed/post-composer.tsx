"use client";

import * as React from "react";
import { Image as ImageIcon, Loader2, Sparkles, X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { getInitials } from "@/lib/utils";
import type { Post, PostGenerateRequest, PostGenerateResponse } from "@/types";

export function PostComposer() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [content, setContent] = React.useState("");
  const [imageUrl, setImageUrl] = React.useState("");
  const [showImageInput, setShowImageInput] = React.useState(false);

  // AI Modal State
  const [aiModalOpen, setAiModalOpen] = React.useState(false);
  const [aiTopic, setAiTopic] = React.useState("");
  const [aiTone, setAiTone] = React.useState<
    "casual" | "professional" | "funny" | "inspirational"
  >("casual");
  const [aiVariants, setAiVariants] = React.useState<string[]>([]);
  const [isGeneratingAi, setIsGeneratingAi] = React.useState(false);

  // Create post mutation
  const createPostMutation = useMutation({
    mutationFn: (data: { content: string; image_url?: string | null }) =>
      apiClient.post<Post>("/posts", data),
    onSuccess: () => {
      setContent("");
      setImageUrl("");
      setShowImageInput(false);
      queryClient.invalidateQueries({ queryKey: ["posts", "feed"] });
      toast({
        title: "Post published!",
        description: "Your post is now live in the community feed.",
      });
    },
    onError: (err: Error) => {
      toast({
        title: "Failed to publish post",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed || trimmed.length > 1000) return;

    createPostMutation.mutate({
      content: trimmed,
      image_url: imageUrl.trim() || null,
    });
  };

  // Generate AI variants
  const handleGenerateAi = async () => {
    const promptSource = aiTopic.trim() || content.trim();
    if (!promptSource) {
      toast({
        title: "Please enter a topic or draft",
        variant: "destructive",
      });
      return;
    }

    setIsGeneratingAi(true);
    setAiVariants([]);
    try {
      const payload: PostGenerateRequest = {
        topic: promptSource,
        draft: content.trim() || null,
        tone: aiTone,
      };
      const res = await apiClient.post<PostGenerateResponse>(
        "/ai/generate-post",
        payload
      );
      setAiVariants(res.variants);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "AI generation failed";
      toast({
        title: "Generation failed",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setIsGeneratingAi(false);
    }
  };

  const handleUseVariant = (variant: string) => {
    setContent(variant);
    setAiModalOpen(false);
    toast({
      title: "AI variant applied!",
      description: "You can further edit or directly publish your post.",
    });
  };

  if (!user) return null;

  const charsRemaining = 1000 - content.length;
  const isTooLong = charsRemaining < 0;

  return (
    <Card className="border shadow-sm mb-6">
      <CardContent className="p-4 sm:p-5">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex items-start space-x-3">
            <Avatar className="h-10 w-10 mt-1 shrink-0">
              {user.avatar_url && (
                <AvatarImage src={user.avatar_url} alt={user.display_name} />
              )}
              <AvatarFallback>{getInitials(user.display_name)}</AvatarFallback>
            </Avatar>

            <div className="flex-1 space-y-2">
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="What's happening on Nexus?"
                rows={3}
                className="w-full resize-none bg-transparent p-1 text-sm sm:text-base outline-none placeholder:text-muted-foreground focus:ring-0"
              />

              {showImageInput && (
                <div className="flex items-center space-x-2 pt-1">
                  <Input
                    type="url"
                    placeholder="Paste image URL (https://...)"
                    value={imageUrl}
                    onChange={(e) => setImageUrl(e.target.value)}
                    className="h-8 text-xs"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setImageUrl("");
                      setShowImageInput(false);
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}

              {imageUrl && (
                <div className="relative mt-2 max-h-48 overflow-hidden rounded-lg border bg-muted">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageUrl}
                    alt="Preview"
                    className="w-full object-cover max-h-48 rounded-lg"
                    onError={() => {
                      toast({
                        title: "Invalid image URL",
                        description: "Could not load image from provided link.",
                        variant: "destructive",
                      });
                      setImageUrl("");
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between border-t pt-3">
            <div className="flex items-center space-x-1 sm:space-x-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowImageInput(!showImageInput)}
                className="text-muted-foreground hover:text-foreground"
              >
                <ImageIcon className="h-4 w-4 mr-1.5" />
                <span className="text-xs">Image</span>
              </Button>

              {/* AI Assist Dialog Trigger */}
              <Dialog open={aiModalOpen} onOpenChange={setAiModalOpen}>
                <DialogTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="text-xs font-semibold text-primary border-primary/30 hover:bg-primary/10"
                    onClick={() => {
                      setAiTopic(content.slice(0, 150));
                      setAiVariants([]);
                    }}
                  >
                    <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                    AI Composer
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle className="flex items-center space-x-2">
                      <Sparkles className="h-5 w-5 text-primary" />
                      <span>AI Post Composer</span>
                    </DialogTitle>
                    <DialogDescription>
                      Generate 3 unique post options tailored to your desired tone.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="ai_topic">Topic or Idea</Label>
                      <Input
                        id="ai_topic"
                        placeholder="e.g. Scaling web applications with event-driven architecture"
                        value={aiTopic}
                        onChange={(e) => setAiTopic(e.target.value)}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label>Tone of Voice</Label>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {(
                          ["casual", "professional", "funny", "inspirational"] as const
                        ).map((tone) => (
                          <Button
                            key={tone}
                            type="button"
                            variant={aiTone === tone ? "default" : "outline"}
                            size="sm"
                            className="text-xs capitalize"
                            onClick={() => setAiTone(tone)}
                          >
                            {tone}
                          </Button>
                        ))}
                      </div>
                    </div>

                    <Button
                      type="button"
                      onClick={handleGenerateAi}
                      disabled={isGeneratingAi}
                      className="w-full"
                    >
                      {isGeneratingAi ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Generating 3 Variants...
                        </>
                      ) : (
                        "Generate Variants"
                      )}
                    </Button>

                    {/* Variant Cards */}
                    {aiVariants.length > 0 && (
                      <div className="space-y-3 pt-2 max-h-72 overflow-y-auto">
                        <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                          Select a Variant:
                        </Label>
                        {aiVariants.map((variant, index) => (
                          <Card
                            key={index}
                            className="p-3 border hover:border-primary transition-all bg-card/60"
                          >
                            <p className="text-xs sm:text-sm text-foreground mb-3 whitespace-pre-wrap">
                              {variant}
                            </p>
                            <Button
                              type="button"
                              size="sm"
                              variant="secondary"
                              className="text-xs h-7"
                              onClick={() => handleUseVariant(variant)}
                            >
                              Use Variant #{index + 1}
                            </Button>
                          </Card>
                        ))}
                      </div>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <div className="flex items-center space-x-3">
              <span
                className={`text-xs ${
                  isTooLong
                    ? "font-bold text-destructive"
                    : charsRemaining < 100
                    ? "text-amber-500 font-semibold"
                    : "text-muted-foreground"
                }`}
              >
                {charsRemaining}
              </span>

              <Button
                type="submit"
                size="sm"
                disabled={
                  !content.trim() ||
                  isTooLong ||
                  createPostMutation.isPending
                }
              >
                {createPostMutation.isPending ? (
                  <>
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    Posting...
                  </>
                ) : (
                  "Post"
                )}
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
