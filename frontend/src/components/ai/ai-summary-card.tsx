"use client";

import * as React from "react";
import { Check, Loader2, Sparkles } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import type { PostSummarizeResponse } from "@/types";

interface AISummaryCardProps {
  postId: string;
  commentsCount: number;
}

export function AISummaryCard({ postId, commentsCount }: AISummaryCardProps) {
  const { toast } = useToast();
  const [summaryData, setSummaryData] = React.useState<PostSummarizeResponse | null>(
    null
  );

  const summarizeMutation = useMutation({
    mutationFn: () =>
      apiClient.post<PostSummarizeResponse>("/ai/summarize", { post_id: postId }),
    onSuccess: (data) => {
      setSummaryData(data);
      toast({ title: "Thread summary generated!" });
    },
    onError: (err: Error) => {
      toast({
        title: "Could not summarize discussion",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  if (commentsCount < 3) {
    return null;
  }

  const sentimentVariant =
    summaryData?.sentiment === "positive"
      ? "success"
      : summaryData?.sentiment === "negative"
      ? "destructive"
      : summaryData?.sentiment === "mixed"
      ? "warning"
      : "secondary";

  return (
    <Card className="border border-primary/20 bg-primary/[0.03] shadow-sm mb-6">
      <CardHeader className="p-4 pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-semibold flex items-center space-x-2 text-primary">
          <Sparkles className="h-4 w-4" />
          <span>AI Thread Summary</span>
        </CardTitle>

        {summaryData && (
          <Badge variant={sentimentVariant} className="capitalize text-[11px]">
            {summaryData.sentiment} Sentiment
          </Badge>
        )}
      </CardHeader>

      <CardContent className="p-4 pt-2">
        {summaryData ? (
          <div className="space-y-3">
            <p className="text-xs sm:text-sm text-foreground/90 leading-relaxed">
              {summaryData.summary}
            </p>

            {summaryData.key_points && summaryData.key_points.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  Key Takeaways
                </span>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {summaryData.key_points.map((pt, i) => (
                    <li key={i} className="flex items-start space-x-2">
                      <Check className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 py-1">
            <p className="text-xs text-muted-foreground">
              This discussion has {commentsCount} comments. Summarize key perspectives and sentiment using Gemini AI.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => summarizeMutation.mutate()}
              disabled={summarizeMutation.isPending}
              className="text-xs text-primary border-primary/30 shrink-0"
            >
              {summarizeMutation.isPending ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                  Summarize Thread
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
