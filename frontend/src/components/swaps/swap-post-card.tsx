"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, GraduationCap, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface SwapPostCardProps {
  content: string;
}

export function SwapPostCard({ content }: SwapPostCardProps) {
  // Parse structured swap post
  const lines = content.split("\n");
  const titleLine = lines[0]?.replace("🔄 Skill Swap Offer:", "").trim() || "Skill Swap Offer";

  let teachSkill = "";
  let wantSkill = "";
  let listingPath = "/swaps";
  const descLines: string[] = [];

  for (const line of lines.slice(1)) {
    if (line.startsWith("I can teach:")) {
      teachSkill = line.replace("I can teach:", "").trim();
    } else if (line.startsWith("Looking for:")) {
      wantSkill = line.replace("Looking for:", "").trim();
    } else if (line.startsWith("Check listing:")) {
      listingPath = line.replace("Check listing:", "").trim();
    } else if (line.trim().length > 0) {
      descLines.push(line);
    }
  }

  const description = descLines.join(" ");

  return (
    <div className="rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-transparent p-4 my-1">
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <Badge className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium flex items-center gap-1.5 px-2.5 py-0.5 text-xs">
          <RefreshCw className="w-3 h-3 animate-spin-slow" />
          Skill Swap Offer
        </Badge>
        <span className="text-[11px] text-muted-foreground font-medium">
          30-min peer exchange
        </span>
      </div>

      <h4 className="text-base font-semibold text-foreground mb-2">{titleLine}</h4>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
        {teachSkill && (
          <div className="flex items-start gap-2 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs">
            <GraduationCap className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="text-muted-foreground block text-[10px] uppercase font-bold tracking-wider">
                Teaches
              </span>
              <span className="font-medium text-foreground">{teachSkill}</span>
            </div>
          </div>
        )}

        {wantSkill && (
          <div className="flex items-start gap-2 p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs">
            <BookOpen className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <span className="text-muted-foreground block text-[10px] uppercase font-bold tracking-wider">
                Wants to learn
              </span>
              <span className="font-medium text-foreground">{wantSkill}</span>
            </div>
          </div>
        )}
      </div>

      {description && (
        <p className="text-xs text-muted-foreground mb-3 line-clamp-2 leading-relaxed">
          {description}
        </p>
      )}

      <div className="pt-2 border-t border-border/50 flex justify-end">
        <Button asChild size="sm" className="gap-1.5 shadow-sm text-xs h-8">
          <Link href={listingPath}>
            <span>Propose a swap</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </Button>
      </div>
    </div>
  );
}
