"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  CalendarCheck,
  Video,
  MapPin,
  Clock,
  ArrowRight,
  Download,
  CheckCircle2,
  AlertTriangle,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SwapNav } from "@/components/swaps/swap-nav";
import { swapApi } from "@/lib/swap-api";
import { getAccessToken } from "@/lib/api-client";
import { SwapSession } from "@/types/swap";

export default function SwapSessionsPage() {
  const [activeTab, setActiveTab] = React.useState<"upcoming" | "completed">("upcoming");

  const { data: sessions, isLoading } = useQuery<SwapSession[]>({
    queryKey: ["swap-sessions"],
    queryFn: async () => {
      return await swapApi.getMySessions();
    },
  });

  const sessionList = sessions || [];
  const upcomingSessions = sessionList.filter(
    (s) => s.status === "scheduled" || s.status === "active"
  );
  const completedSessions = sessionList.filter(
    (s) => s.status === "completed" || s.status === "disputed" || s.status === "cancelled"
  );

  const handleDownloadIcs = async (sessionId: string) => {
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

  const renderSessionCard = (session: SwapSession) => {
    const halves = session.halves || [];
    const firstHalf = halves.find((h) => h.half_number === 1);
    const secondHalf = halves.find((h) => h.half_number === 2);

    const startTime = firstHalf ? new Date(firstHalf.start_time_utc) : new Date(session.created_at);
    const endTime = secondHalf ? new Date(secondHalf.end_time_utc) : new Date(startTime.getTime() + 60 * 60 * 1000);

    const isUpcoming = session.status === "scheduled" || session.status === "active";

    return (
      <Card key={session.id} className="overflow-hidden border hover:border-primary/40 transition-colors">
        <CardContent className="p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                {session.mode === "video" ? <Video className="w-5 h-5" /> : <MapPin className="w-5 h-5" />}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">
                    Swap with @{session.user_b.username}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {session.mode === "video" ? "Jitsi Video" : "In-Person"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                  <Clock className="w-3.5 h-3.5" />
                  <span>
                    {startTime.toLocaleDateString(undefined, {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                    })}
                    , {startTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} &ndash;{" "}
                    {endTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto">
              {session.status === "scheduled" && (
                <Badge className="bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-300">
                  Scheduled
                </Badge>
              )}
              {session.status === "active" && (
                <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-300 animate-pulse">
                  Active Now
                </Badge>
              )}
              {session.status === "completed" && (
                <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-300">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Completed
                </Badge>
              )}
              {session.status === "disputed" && (
                <Badge variant="destructive">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  Disputed
                </Badge>
              )}
            </div>
          </div>

          {/* Halves Breakdown Matrix */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-muted/30 rounded-lg text-xs">
            <div className="space-y-1">
              <span className="text-muted-foreground font-semibold flex items-center gap-1">
                <span className="w-4 h-4 rounded-full bg-primary/20 text-primary font-bold flex items-center justify-center text-[10px]">
                  1
                </span>
                Half 1 (30m):
              </span>
              <p className="font-semibold text-foreground pl-5">
                {firstHalf?.mentor.display_name} &rarr; {firstHalf?.learner.display_name}
              </p>
              <p className="text-muted-foreground pl-5 font-medium text-[11px]">
                Skill: {firstHalf?.skill.display_name}
              </p>
            </div>

            <div className="space-y-1 sm:border-l sm:pl-3">
              <span className="text-muted-foreground font-semibold flex items-center gap-1">
                <span className="w-4 h-4 rounded-full bg-primary/20 text-primary font-bold flex items-center justify-center text-[10px]">
                  2
                </span>
                Half 2 (30m):
              </span>
              <p className="font-semibold text-foreground pl-5">
                {secondHalf?.mentor.display_name} &rarr; {secondHalf?.learner.display_name}
              </p>
              <p className="text-muted-foreground pl-5 font-medium text-[11px]">
                Skill: {secondHalf?.skill.display_name}
              </p>
            </div>
          </div>

          {/* Location info if in-person */}
          {session.mode === "in_person" && session.public_place_name && (
            <div className="text-xs p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-md text-amber-900 dark:text-amber-200 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                <strong>Meeting Location:</strong> {session.public_place_name}{" "}
                {session.public_place_address && `(${session.public_place_address})`}
              </span>
            </div>
          )}

          {/* Action Row */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5"
              onClick={() => handleDownloadIcs(session.id)}
            >
              <Download className="w-3.5 h-3.5" />
              Download .ics
            </Button>

            <Link href={`/swaps/sessions/${session.id}`}>
              <Button size="sm" className="h-8 text-xs gap-1.5">
                <span>{isUpcoming ? "Enter Session Room" : "View Session Details"}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="container max-w-5xl py-6 space-y-6">
      <SwapNav activeSessionsCount={upcomingSessions.length} />

      <div>
        <h1 className="text-2xl font-bold tracking-tight">My Swap Sessions</h1>
        <p className="text-sm text-muted-foreground">
          View your upcoming confirmed mentorship sessions, join video rooms, and download calendar events.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "upcoming" | "completed")} className="w-full">
        <TabsList className="grid w-full sm:w-[400px] grid-cols-2">
          <TabsTrigger value="upcoming" className="gap-2">
            <span>Upcoming Scheduled</span>
            {upcomingSessions.length > 0 && (
              <Badge className="h-5 px-1.5 text-[10px] bg-primary text-primary-foreground">
                {upcomingSessions.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="completed">
            Completed History ({completedSessions.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming" className="space-y-4 pt-4">
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground text-sm">
              Loading sessions...
            </div>
          ) : upcomingSessions.length === 0 ? (
            <div className="text-center py-16 border rounded-xl bg-muted/20 space-y-3">
              <Calendar className="w-10 h-10 text-muted-foreground mx-auto opacity-50" />
              <p className="text-sm font-semibold text-muted-foreground">No upcoming sessions</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Once a swap proposal is accepted by either party, your scheduled meeting will appear right here.
              </p>
              <Link href="/swaps">
                <Button size="sm" variant="outline" className="mt-2 text-xs">
                  Explore Swaps
                </Button>
              </Link>
            </div>
          ) : (
            upcomingSessions.map(renderSessionCard)
          )}
        </TabsContent>

        <TabsContent value="completed" className="space-y-4 pt-4">
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground text-sm">
              Loading sessions...
            </div>
          ) : completedSessions.length === 0 ? (
            <div className="text-center py-16 border rounded-xl bg-muted/20 space-y-3">
              <CalendarCheck className="w-10 h-10 text-muted-foreground mx-auto opacity-50" />
              <p className="text-sm font-semibold text-muted-foreground">No completed sessions yet</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Completed skill swaps and revealed double-blind peer feedback will be archived here.
              </p>
            </div>
          ) : (
            completedSessions.map(renderSessionCard)
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
