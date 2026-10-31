"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  GraduationCap,
  Loader2,
  MessageSquare,
  Search,
  Send,
  UserCheck,
} from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { formatRelativeTime, getInitials } from "@/lib/utils";
import type {
  ConversationResponse,
  DirectMessageResponse,
  FriendUserResponse,
  User,
} from "@/types";

function MessagesContent() {
  const { user: currentUser } = useAuth();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const targetUserIdParam = searchParams.get("user");

  const [activeConvId, setActiveConvId] = React.useState<string | null>(null);
  const [activeRecipient, setActiveRecipient] = React.useState<User | null>(null);
  const [inputText, setInputText] = React.useState("");
  const [searchFilter, setSearchFilter] = React.useState("");

  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // 1. Fetch all conversations
  const { data: conversations, isLoading: isLoadingConvs } = useQuery<ConversationResponse[]>({
    queryKey: ["messages", "conversations"],
    queryFn: () => apiClient.get<ConversationResponse[]>("/messages/conversations"),
    refetchInterval: 4000,
  });

  // 2. Fetch friends to resolve deep-link recipient if not in active conversations
  const { data: friends } = useQuery<FriendUserResponse[]>({
    queryKey: ["friends", "list"],
    queryFn: () => apiClient.get<FriendUserResponse[]>("/friends"),
    enabled: !!targetUserIdParam && !activeRecipient,
  });

  // Handle URL deep-link (?user=<id>)
  React.useEffect(() => {
    if (!targetUserIdParam) return;

    if (conversations && conversations.length > 0) {
      const match = conversations.find((c) => c.other_user.id === targetUserIdParam);
      if (match) {
        setActiveConvId(match.id);
        setActiveRecipient(match.other_user);
        return;
      }
    }

    if (friends && friends.length > 0) {
      const friendMatch = friends.find((f) => f.friend.id === targetUserIdParam);
      if (friendMatch) {
        setActiveRecipient(friendMatch.friend);
        setActiveConvId(null);
      }
    }
  }, [targetUserIdParam, conversations, friends]);

  // 3. Fetch active conversation messages
  const { data: messages, isLoading: isLoadingMessages } = useQuery<DirectMessageResponse[]>({
    queryKey: ["messages", "thread", activeConvId],
    queryFn: () => apiClient.get<DirectMessageResponse[]>(`/messages/${activeConvId}`),
    enabled: !!activeConvId,
    refetchInterval: 3000,
  });

  // Auto-scroll to latest message
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: (content: string) => {
      if (!activeRecipient) throw new Error("No recipient selected");
      return apiClient.post<DirectMessageResponse>("/messages/send", {
        receiver_id: activeRecipient.id,
        content,
      });
    },
    onSuccess: (newMsg) => {
      setInputText("");
      if (!activeConvId) {
        setActiveConvId(newMsg.conversation_id);
      }
      queryClient.invalidateQueries({ queryKey: ["messages"] });
    },
    onError: (err: Error) => {
      toast({
        title: "Could not send message",
        description: err.message || "Failed to deliver message.",
        variant: "destructive",
      });
    },
  });

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = inputText.trim();
    if (!clean || sendMutation.isPending) return;
    sendMutation.mutate(clean);
  };

  const filteredConversations = conversations?.filter((c) => {
    const q = searchFilter.toLowerCase().trim();
    if (!q) return true;
    return (
      c.other_user.display_name.toLowerCase().includes(q) ||
      c.other_user.username.toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-5xl mx-auto h-[calc(100vh-10.5rem)] md:h-[calc(100vh-7rem)] flex border rounded-xl overflow-hidden bg-card shadow-sm">
      {/* ── Left Sidebar: Conversations List ── */}
      <div
        className={`w-full md:w-72 lg:w-80 border-r flex flex-col shrink-0 bg-background ${activeRecipient ? "hidden md:flex" : "flex"
          }`}
      >
        <div className="p-3 border-b space-y-2 bg-muted/20 shrink-0">
          <div className="flex items-center justify-between">
            <h1 className="font-bold text-sm sm:text-base flex items-center space-x-2 text-foreground">
              <MessageSquare className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
              <span>Direct Messages</span>
            </h1>
            <Link href="/friends">
              <Button variant="ghost" size="sm" className="h-7 text-xs text-primary px-2 hover:bg-primary/10">
                + New Chat
              </Button>
            </Link>
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search conversations..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="pl-8 h-8 text-xs bg-card"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-border/60">
          {isLoadingConvs ? (
            <div className="text-center py-8 text-xs text-muted-foreground">Loading chats...</div>
          ) : !filteredConversations || filteredConversations.length === 0 ? (
            <div className="text-center py-10 px-4 text-xs text-muted-foreground space-y-2.5">
              <p>No active conversations yet.</p>
              <Link href="/friends">
                <Button variant="outline" size="sm" className="text-xs">
                  Message a Friend
                </Button>
              </Link>
            </div>
          ) : (
            filteredConversations.map((c) => {
              const isSelected = activeRecipient?.id === c.other_user.id;
              return (
                <button
                  key={c.id}
                  onClick={() => {
                    setActiveConvId(c.id);
                    setActiveRecipient(c.other_user);
                  }}
                  className={`w-full p-3 flex items-start space-x-3 text-left transition-colors hover:bg-muted/50 ${isSelected ? "bg-muted/80 border-l-4 border-primary" : ""
                    }`}
                >
                  <Avatar className="h-10 w-10 shrink-0 border shadow-xs">
                    {c.other_user.avatar_url && (
                      <AvatarImage src={c.other_user.avatar_url} alt={c.other_user.display_name} />
                    )}
                    <AvatarFallback className="text-xs font-semibold">
                      {getInitials(c.other_user.display_name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs truncate text-foreground">
                        {c.other_user.display_name}
                      </span>
                      {c.last_message && (
                        <span className="text-[10px] text-muted-foreground shrink-0 ml-1">
                          {formatRelativeTime(c.last_message.created_at)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between mt-0.5">
                      <p className="text-xs text-muted-foreground truncate">
                        {c.last_message ? c.last_message.content : "Started conversation"}
                      </p>
                      {c.unread_count > 0 && (
                        <span className="ml-1.5 shrink-0 inline-flex items-center justify-center h-4.5 min-w-[18px] px-1 bg-primary text-primary-foreground text-[10px] font-bold rounded-full">
                          {c.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* ── Right Pane: Active Chat Window ── */}
      <div className={`flex-1 min-w-0 flex flex-col bg-background ${!activeRecipient ? "hidden md:flex" : "flex"}`}>
        {activeRecipient ? (
          <>
            {/* Chat Header */}
            <div className="h-14 px-3 sm:px-4 border-b flex items-center justify-between bg-muted/20 shrink-0">
              <div className="flex items-center space-x-2.5 sm:space-x-3 min-w-0">
                <Button
                  variant="ghost"
                  size="icon"
                  className="md:hidden h-8 w-8 -ml-1 text-muted-foreground shrink-0"
                  onClick={() => {
                    setActiveRecipient(null);
                    setActiveConvId(null);
                  }}
                  title="Back to conversations"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
                <Link
                  href={`/profile/${activeRecipient.username}`}
                  className="flex items-center space-x-2.5 hover:opacity-85 min-w-0"
                >
                  <Avatar className="h-8 w-8 border shrink-0">
                    {activeRecipient.avatar_url && (
                      <AvatarImage src={activeRecipient.avatar_url} alt={activeRecipient.display_name} />
                    )}
                    <AvatarFallback className="text-xs font-semibold">
                      {getInitials(activeRecipient.display_name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <h2 className="text-xs sm:text-sm font-bold text-foreground leading-none truncate">
                      {activeRecipient.display_name}
                    </h2>
                    <p className="text-[11px] text-muted-foreground leading-tight mt-0.5 truncate">
                      @{activeRecipient.username}
                    </p>
                  </div>
                </Link>
              </div>

              {activeRecipient.usn && (
                <div className="flex items-center space-x-1 text-[11px] text-primary font-medium bg-primary/10 px-2 py-0.5 rounded-md shrink-0">
                  <GraduationCap className="h-3 w-3" />
                  <span className="hidden sm:inline">{activeRecipient.usn}</span>
                </div>
              )}
            </div>

            {/* Chat Messages Flow */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3">
              {isLoadingMessages ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : !messages || messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center p-6 text-muted-foreground space-y-2">
                  <UserCheck className="h-10 w-10 text-primary/40 mb-1" />
                  <p className="text-sm font-semibold text-foreground">
                    Connected with {activeRecipient.display_name}
                  </p>
                  <p className="text-xs max-w-xs">
                    Send a friendly message below to start your conversation!
                  </p>
                </div>
              ) : (
                messages.map((m) => {
                  const isMe = m.sender_id === currentUser?.id;
                  return (
                    <div
                      key={m.id}
                      className={`flex ${isMe ? "justify-end" : "justify-start"}`}
                    >
                      {!isMe && (
                        <Avatar className="h-7 w-7 mr-2 mt-0.5 shrink-0 border">
                          {activeRecipient.avatar_url && (
                            <AvatarImage src={activeRecipient.avatar_url} alt={activeRecipient.display_name} />
                          )}
                          <AvatarFallback className="text-[10px]">
                            {getInitials(activeRecipient.display_name)}
                          </AvatarFallback>
                        </Avatar>
                      )}
                      <div className="max-w-[78%] sm:max-w-[70%] space-y-1">
                        <div
                          className={`rounded-2xl px-3.5 py-2 text-xs sm:text-sm whitespace-pre-wrap leading-relaxed shadow-xs break-words ${isMe
                              ? "bg-primary text-primary-foreground rounded-tr-xs"
                              : "bg-muted text-foreground border rounded-tl-xs"
                            }`}
                        >
                          {m.content}
                        </div>
                        <p
                          className={`text-[9px] text-muted-foreground px-1 ${isMe ? "text-right" : "text-left"
                            }`}
                        >
                          {formatRelativeTime(m.created_at)}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Chat Input Bar */}
            <form
              onSubmit={handleSendMessage}
              className="p-2.5 sm:p-3 border-t flex items-center space-x-2 bg-muted/20 shrink-0"
            >
              <Input
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={`Message @${activeRecipient.username}...`}
                disabled={sendMutation.isPending}
                className="text-xs sm:text-sm h-10 bg-background"
                autoFocus
              />
              <Button
                type="submit"
                size="icon"
                disabled={!inputText.trim() || sendMutation.isPending}
                className="h-10 w-10 shrink-0 bg-primary text-primary-foreground shadow-sm"
              >
                {sendMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8 text-muted-foreground space-y-3">
            <div className="p-3.5 rounded-full bg-primary/10 text-primary">
              <MessageSquare className="h-8 w-8" />
            </div>
            <p className="font-semibold text-foreground text-base">Select a conversation</p>
            <p className="text-xs max-w-sm text-muted-foreground">
              Choose an active chat from the list on the left, or open the Friends page to start a chat with classmates.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function MessagesPage() {
  return (
    <React.Suspense
      fallback={
        <div className="max-w-5xl mx-auto h-[calc(100vh-10.5rem)] md:h-[calc(100vh-7rem)] flex items-center justify-center border rounded-xl bg-card">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      }
    >
      <MessagesContent />
    </React.Suspense>
  );
}
