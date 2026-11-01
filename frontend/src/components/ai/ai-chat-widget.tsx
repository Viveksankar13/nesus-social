"use client";

import * as React from "react";
import {
  Bot,
  ChevronDown,
  Loader2,
  Plus,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient, getAccessToken } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import type {
  AIChatMessage,
  AIChatSession,
  AIChatSessionDetail,
} from "@/types";

function formatChatMessage(text: string): string {
  if (!text) return "";
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1") // Strip **bold**
    .replace(/\*(.*?)\*/g, "$1") // Strip *italic*
    .replace(/^#+\s+/gm, "") // Strip # headers
    .replace(/^\s*\*\s+/gm, "• "); // Convert * bullets to •
}

export function AIChatWidget() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [isOpen, setIsOpen] = React.useState(false);
  const [activeSessionId, setActiveSessionId] = React.useState<string | null>(
    null
  );
  const [inputMessage, setInputMessage] = React.useState("");
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [streamedText, setStreamedText] = React.useState("");

  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Scroll to bottom helper
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // 1. Fetch user's chat sessions
  const { data: sessions } = useQuery<AIChatSession[]>({
    queryKey: ["ai", "chat", "sessions"],
    queryFn: () => apiClient.get<AIChatSession[]>("/ai/chat/sessions"),
    enabled: !!user && isOpen,
  });

  // Select first session if none active
  React.useEffect(() => {
    if (sessions && sessions.length > 0 && !activeSessionId) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  // 2. Fetch active session messages
  const { data: sessionDetail, isLoading: isLoadingSession } =
    useQuery<AIChatSessionDetail>({
      queryKey: ["ai", "chat", "session", activeSessionId],
      queryFn: () =>
        apiClient.get<AIChatSessionDetail>(`/ai/chat/sessions/${activeSessionId}`),
      enabled: !!user && !!activeSessionId && isOpen,
    });

  React.useEffect(() => {
    scrollToBottom();
  }, [sessionDetail?.messages, streamedText]);

  // Create new session
  const handleNewSession = async () => {
    try {
      const newSession = await apiClient.post<AIChatSession>(
        "/ai/chat/sessions",
        { title: "New Conversation" }
      );
      queryClient.invalidateQueries({ queryKey: ["ai", "chat", "sessions"] });
      setActiveSessionId(newSession.id);
      setStreamedText("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Could not create chat";
      toast({ title: "Error", description: msg, variant: "destructive" });
    }
  };

  // Send message via streaming SSE
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputMessage.trim();
    if (!text || isStreaming) return;

    let targetSessionId = activeSessionId;
    if (!targetSessionId) {
      try {
        const newSession = await apiClient.post<AIChatSession>(
          "/ai/chat/sessions",
          { title: text.slice(0, 30) }
        );
        targetSessionId = newSession.id;
        setActiveSessionId(newSession.id);
      } catch {
        toast({ title: "Failed to initialize conversation", variant: "destructive" });
        return;
      }
    }

    setInputMessage("");
    setIsStreaming(true);
    setStreamedText("");

    try {
      const token = getAccessToken();
      const response = await fetch("/api/v1/ai/chat/message", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          session_id: targetSessionId,
          message: text,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat request failed (${response.status})`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");

      if (!reader) {
        throw new Error("No response stream");
      }

      let accumulated = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const rawChunk = decoder.decode(value, { stream: true });
        const lines = rawChunk.split("\n");

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            const dataStr = trimmed.slice(6);
            if (dataStr === "[DONE]") {
              break;
            }
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.chunk) {
                accumulated += parsed.chunk;
                setStreamedText(accumulated);
              }
            } catch {
              // ignore parse errors
            }
          }
        }
      }

      // Stream complete: refresh session messages
      queryClient.invalidateQueries({
        queryKey: ["ai", "chat", "session", targetSessionId],
      });
      queryClient.invalidateQueries({ queryKey: ["ai", "chat", "sessions"] });
      setStreamedText("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Streaming failed";
      toast({
        title: "Assistant error",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setIsStreaming(false);
    }
  };

  if (!user) return null;

  return (
    <div className="fixed bottom-20 right-4 md:bottom-6 md:right-6 z-50">
      {/* Floating launcher button */}
      {!isOpen && (
        <Button
          onClick={() => setIsOpen(true)}
          className="h-12 w-12 sm:h-13 sm:w-13 rounded-full shadow-xl bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-500 text-primary-foreground p-3 transition-transform hover:scale-105 active:scale-95 touch-manipulation"
          aria-label="Open Nexus AI Assistant"
        >
          <Sparkles className="h-5 w-5 sm:h-6 sm:w-6" />
        </Button>
      )}

      {/* Chat Window Panel */}
      {isOpen && (
        <Card className="w-[calc(100vw-2rem)] max-w-[400px] sm:w-[420px] h-[min(540px,calc(100vh-7rem))] shadow-2xl border flex flex-col overflow-hidden bg-background">
          {/* Header */}
          <CardHeader className="p-3.5 bg-muted/40 border-b flex flex-row items-center justify-between shrink-0">
            <div className="flex items-center space-x-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Bot className="h-4 w-4" />
              </div>

              {/* Sessions Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center space-x-1 text-xs font-semibold text-foreground hover:text-primary max-w-[170px] truncate text-left">
                    <span className="truncate">
                      {sessionDetail?.title || "Nexus Companion"}
                    </span>
                    <ChevronDown className="h-3 w-3 shrink-0" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-52">
                  {sessions?.map((s) => (
                    <DropdownMenuItem
                      key={s.id}
                      onClick={() => setActiveSessionId(s.id)}
                      className="cursor-pointer text-xs truncate"
                    >
                      {s.title}
                    </DropdownMenuItem>
                  ))}
                  {(!sessions || sessions.length === 0) && (
                    <div className="p-2 text-xs text-muted-foreground">
                      No previous sessions
                    </div>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                onClick={handleNewSession}
                title="New Chat"
              >
                <Plus className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                onClick={() => setIsOpen(false)}
                title="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>

          {/* Messages Feed */}
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-3 text-xs sm:text-sm">
            {isLoadingSession ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : (!sessionDetail?.messages || sessionDetail.messages.length === 0) &&
              !streamedText ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-4 space-y-2 text-muted-foreground">
                <Sparkles className="h-8 w-8 text-primary/50" />
                <p className="font-semibold text-foreground">Nexus AI Support & Assistant</p>
                <p className="text-xs">
                  Ask me for help with platform issues, account assistance, troubleshooting, or post drafting.
                </p>
              </div>
            ) : (
              <>
                {sessionDetail?.messages.map((m: AIChatMessage) => {
                  const isUser = m.role === "user";
                  return (
                    <div
                      key={m.id}
                      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                    >
                      {!isUser && (
                        <Avatar className="h-6 w-6 mr-2 shrink-0 mt-0.5">
                          <AvatarFallback className="bg-primary/10 text-primary text-[10px]">
                            AI
                          </AvatarFallback>
                        </Avatar>
                      )}
                      <div
                        className={`rounded-2xl px-3.5 py-2 max-w-[80%] whitespace-pre-wrap leading-relaxed ${isUser
                            ? "bg-primary text-primary-foreground rounded-br-xs"
                            : "bg-muted text-foreground rounded-bl-xs border"
                          }`}
                      >
                        {formatChatMessage(m.content)}
                      </div>
                    </div>
                  );
                })}

                {/* Live stream bubble */}
                {isStreaming && (
                  <div className="flex justify-start">
                    <Avatar className="h-6 w-6 mr-2 shrink-0 mt-0.5">
                      <AvatarFallback className="bg-primary/10 text-primary text-[10px]">
                        AI
                      </AvatarFallback>
                    </Avatar>
                    <div className="rounded-2xl rounded-bl-xs bg-muted text-foreground border px-3.5 py-2 max-w-[80%] whitespace-pre-wrap leading-relaxed">
                      {streamedText ? (
                        formatChatMessage(streamedText)
                      ) : (
                        <div className="flex items-center space-x-1.5 py-1">
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse delay-150" />
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse delay-300" />
                        </div>
                      )}
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </CardContent>

          {/* Message input footer */}
          <form
            onSubmit={handleSendMessage}
            className="p-3 border-t bg-muted/20 flex items-center space-x-2 shrink-0"
          >
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask for support, report an issue, or ask a question..."
              disabled={isStreaming}
              className="text-xs sm:text-sm h-9"
            />
            <Button
              type="submit"
              size="icon"
              disabled={!inputMessage.trim() || isStreaming}
              className="h-9 w-9 shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}
