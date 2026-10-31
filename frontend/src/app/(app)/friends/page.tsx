"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  GraduationCap,
  MessageSquare,
  Search,
  UserMinus,
  Users,
  X,
} from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { getInitials } from "@/lib/utils";
import type { FriendRequestsData, FriendUserResponse } from "@/types";

export default function FriendsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = React.useState("");

  // 1. Fetch Friends
  const { data: friends, isLoading: isLoadingFriends } = useQuery<FriendUserResponse[]>({
    queryKey: ["friends", "list"],
    queryFn: () => apiClient.get<FriendUserResponse[]>("/friends"),
  });

  // 2. Fetch Requests
  const { data: requests, isLoading: isLoadingRequests } = useQuery<FriendRequestsData>({
    queryKey: ["friends", "requests"],
    queryFn: () => apiClient.get<FriendRequestsData>("/friends/requests"),
  });

  // Mutations
  const acceptMutation = useMutation({
    mutationFn: (requestId: string) => apiClient.post(`/friends/accept/${requestId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["friends"] });
      toast({ title: "Connected", description: "Friend request accepted!" });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (requestId: string) => apiClient.post(`/friends/reject/${requestId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["friends"] });
      toast({ title: "Declined", description: "Friend request declined." });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => apiClient.delete(`/friends/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["friends"] });
      toast({ title: "Removed", description: "Friend connection removed." });
    },
  });

  const incomingCount = requests?.incoming?.length || 0;

  const filteredFriends = friends?.filter((f) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      f.friend.display_name.toLowerCase().includes(q) ||
      f.friend.username.toLowerCase().includes(q) ||
      (f.friend.usn && f.friend.usn.toLowerCase().includes(q))
    );
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Friends & Network</h1>
            <p className="text-xs text-muted-foreground">
              Connect with classmates, collaborate, and chat privately
            </p>
          </div>
        </div>
      </div>

      <Tabs defaultValue="friends" className="space-y-5">
        <TabsList className="grid w-full grid-cols-2 h-11 bg-muted/60 p-1">
          <TabsTrigger value="friends" className="text-xs sm:text-sm font-medium">
            All Friends ({friends?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="requests" className="text-xs sm:text-sm font-medium relative">
            Friend Requests
            {incomingCount > 0 && (
              <span className="ml-2 inline-flex items-center justify-center h-4.5 min-w-[18px] px-1 text-[10px] font-bold bg-primary text-primary-foreground rounded-full">
                {incomingCount}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: All Friends */}
        <TabsContent value="friends" className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search friends by name, username, or student USN..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-10 text-sm bg-background"
            />
          </div>

          {isLoadingFriends ? (
            <div className="text-center py-12 text-sm text-muted-foreground">Loading your friends...</div>
          ) : !filteredFriends || filteredFriends.length === 0 ? (
            <Card className="border-dashed p-10 text-center text-muted-foreground space-y-2">
              <Users className="h-10 w-10 mx-auto text-muted-foreground/40 mb-1" />
              <p className="font-semibold text-foreground text-sm">No friends found</p>
              <p className="text-xs max-w-sm mx-auto">
                Discover classmates on the community feed or search by student USN to send friend requests!
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {filteredFriends.map((f) => (
                <Card
                  key={f.friendship_id}
                  className="p-3.5 flex items-center justify-between hover:shadow-sm transition-all border bg-card"
                >
                  <div className="flex items-center space-x-3 min-w-0 flex-1 mr-2">
                    <Link href={`/profile/${f.friend.username}`} className="shrink-0">
                      <Avatar className="h-11 w-11 border shadow-xs">
                        {f.friend.avatar_url && (
                          <AvatarImage src={f.friend.avatar_url} alt={f.friend.display_name} />
                        )}
                        <AvatarFallback className="font-semibold text-xs">
                          {getInitials(f.friend.display_name)}
                        </AvatarFallback>
                      </Avatar>
                    </Link>
                    <div className="min-w-0 flex-1">
                      <Link
                        href={`/profile/${f.friend.username}`}
                        className="font-semibold text-sm hover:underline block truncate text-foreground leading-snug"
                      >
                        {f.friend.display_name}
                      </Link>
                      <p className="text-xs text-muted-foreground truncate leading-tight">
                        @{f.friend.username}
                      </p>
                      {f.friend.usn && (
                        <div className="inline-flex items-center space-x-1 mt-1 text-[10px] text-primary font-medium bg-primary/10 px-2 py-0.5 rounded-md">
                          <GraduationCap className="h-3 w-3 shrink-0" />
                          <span className="truncate">{f.friend.usn}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-1.5 shrink-0">
                    <Button
                      size="sm"
                      className="h-8 px-3 text-xs bg-primary text-primary-foreground flex items-center space-x-1.5 shadow-sm"
                      onClick={() => router.push(`/messages?user=${f.friend.id}`)}
                      title="Send Message"
                    >
                      <MessageSquare className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">Message</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      onClick={() => removeMutation.mutate(f.friend.id)}
                      title="Unfriend"
                    >
                      <UserMinus className="h-4 w-4" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Tab 2: Friend Requests */}
        <TabsContent value="requests" className="space-y-6">
          {/* Incoming */}
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Incoming Requests ({incomingCount})
            </h2>
            {isLoadingRequests ? (
              <p className="text-xs text-muted-foreground">Loading requests...</p>
            ) : incomingCount === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No incoming friend requests at the moment.</p>
            ) : (
              <div className="space-y-2.5">
                {requests?.incoming.map((req) => (
                  <Card key={req.id} className="p-3.5 flex items-center justify-between border bg-card">
                    <div className="flex items-center space-x-3 min-w-0 flex-1 mr-2">
                      <Link href={`/profile/${req.sender.username}`} className="shrink-0">
                        <Avatar className="h-10 w-10 border">
                          {req.sender.avatar_url && (
                            <AvatarImage src={req.sender.avatar_url} alt={req.sender.display_name} />
                          )}
                          <AvatarFallback className="text-xs font-semibold">
                            {getInitials(req.sender.display_name)}
                          </AvatarFallback>
                        </Avatar>
                      </Link>
                      <div className="min-w-0 flex-1">
                        <Link
                          href={`/profile/${req.sender.username}`}
                          className="font-semibold text-sm hover:underline block truncate text-foreground"
                        >
                          {req.sender.display_name}
                        </Link>
                        <p className="text-xs text-muted-foreground truncate">@{req.sender.username}</p>
                        {req.sender.usn && (
                          <Badge variant="outline" className="text-[10px] mt-0.5">
                            {req.sender.usn}
                          </Badge>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <Button
                        size="sm"
                        className="h-8 px-3 text-xs bg-emerald-600 hover:bg-emerald-700 text-white flex items-center space-x-1 shadow-sm font-medium"
                        onClick={() => acceptMutation.mutate(req.id)}
                      >
                        <Check className="h-3.5 w-3.5" />
                        <span>Accept</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 px-2.5 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        onClick={() => rejectMutation.mutate(req.id)}
                        title="Decline"
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Outgoing */}
          <div className="space-y-3 pt-4 border-t">
            <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Sent Requests ({requests?.outgoing?.length || 0})
            </h2>
            {!requests?.outgoing || requests.outgoing.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No pending sent requests.</p>
            ) : (
              <div className="space-y-2.5">
                {requests.outgoing.map((req) => (
                  <Card key={req.id} className="p-3.5 flex items-center justify-between border bg-card">
                    <div className="flex items-center space-x-3 min-w-0 flex-1 mr-2">
                      <Link href={`/profile/${req.receiver.username}`} className="shrink-0">
                        <Avatar className="h-10 w-10 border">
                          {req.receiver.avatar_url && (
                            <AvatarImage src={req.receiver.avatar_url} alt={req.receiver.display_name} />
                          )}
                          <AvatarFallback className="text-xs font-semibold">
                            {getInitials(req.receiver.display_name)}
                          </AvatarFallback>
                        </Avatar>
                      </Link>
                      <div className="min-w-0 flex-1">
                        <Link
                          href={`/profile/${req.receiver.username}`}
                          className="font-semibold text-sm hover:underline block truncate text-foreground"
                        >
                          {req.receiver.display_name}
                        </Link>
                        <p className="text-xs text-muted-foreground truncate">@{req.receiver.username}</p>
                      </div>
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10 shrink-0"
                      onClick={() => removeMutation.mutate(req.receiver_id)}
                    >
                      Cancel
                    </Button>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
