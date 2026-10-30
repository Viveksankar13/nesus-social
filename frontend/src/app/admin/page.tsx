"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Heart,
  MessageCircle,
  ShieldAlert,
  TrendingUp,
  UserCheck,
  UserPlus,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiClient } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AdminStatsResponse, ChartDataResponse } from "@/types";

export default function AdminDashboardPage() {
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  // 1. Fetch KPI Statistics
  const {
    data: stats,
    isLoading: statsLoading,
  } = useQuery<AdminStatsResponse>({
    queryKey: ["admin", "stats"],
    queryFn: () => apiClient.get<AdminStatsResponse>("/admin/stats"),
    refetchInterval: 30000,
  });

  // 2. Fetch 30-Day Time Series Charts
  const {
    data: charts,
    isLoading: chartsLoading,
  } = useQuery<ChartDataResponse>({
    queryKey: ["admin", "charts"],
    queryFn: () => apiClient.get<ChartDataResponse>("/admin/charts"),
    staleTime: 60000,
  });

  return (
    <div className="space-y-8">
      {/* Page Title & Status */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">
            System health, platform-wide analytics, and automated moderation overview
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/admin/moderation">
            <Button variant="outline" size="sm" className="gap-2">
              <ShieldAlert className="h-4 w-4 text-amber-500" />
              Review Moderation Queue
              {stats?.flagged_items ? (
                <Badge variant="destructive" className="ml-1 text-xs">
                  {stats.flagged_items}
                </Badge>
              ) : null}
            </Button>
          </Link>
        </div>
      </div>

      {/* 6 KPI Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Total Users */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div>
                <div className="text-2xl font-bold">{stats?.total_users ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                  <UserCheck className="h-3.5 w-3.5 text-emerald-500" />
                  <span>{stats?.verified_users ?? 0} verified accounts</span>
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* New Users (7d) */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">New Signups (7d)</CardTitle>
            <UserPlus className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div>
                <div className="text-2xl font-bold">{stats?.new_users_7d ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                  <TrendingUp className="h-3.5 w-3.5 text-indigo-500" />
                  <span>Growth in last 7 days</span>
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Total Posts */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Posts</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div>
                <div className="text-2xl font-bold">{stats?.total_posts ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Public and active discussions
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Total Comments */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Comments</CardTitle>
            <MessageCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div>
                <div className="text-2xl font-bold">{stats?.total_comments ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  User replies and conversations
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Total Likes */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Reactions</CardTitle>
            <Heart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div>
                <div className="text-2xl font-bold">{stats?.total_likes ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5 text-rose-500" />
                  <span>User engagement likes</span>
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Flagged Items */}
        <Card className={stats?.flagged_items ? "border-amber-500/40 bg-amber-500/5" : ""}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Flagged Items</CardTitle>
            <ShieldAlert className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div>
                <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                  {stats?.flagged_items ?? 0}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Pending automated / report moderation
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 2 Recharts Analytics Charts (30 Days) */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* User Signups 30d */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">User Signups (Last 30 Days)</CardTitle>
            <CardDescription>
              New registered accounts per day across the platform
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[280px] w-full">
              {chartsLoading || !isMounted ? (
                <div className="flex h-full items-center justify-center">
                  <Skeleton className="h-full w-full rounded-md" />
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={charts?.signups_by_day ?? []}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="signupGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(val) => {
                        const d = new Date(val);
                        return `${d.getMonth() + 1}/${d.getDate()}`;
                      }}
                      className="text-xs text-muted-foreground"
                    />
                    <YAxis allowDecimals={false} className="text-xs text-muted-foreground" />
                    <Tooltip
                      labelFormatter={(label) => `Date: ${label}`}
                      formatter={(val: number) => [`${val} Signups`, "Users"]}
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        borderColor: "hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="count"
                      stroke="#6366f1"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#signupGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Posts Created 30d */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Post Activity (Last 30 Days)</CardTitle>
            <CardDescription>
              New posts and discussion topics submitted per day
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[280px] w-full">
              {chartsLoading || !isMounted ? (
                <div className="flex h-full items-center justify-center">
                  <Skeleton className="h-full w-full rounded-md" />
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={charts?.posts_by_day ?? []}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="postGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(val) => {
                        const d = new Date(val);
                        return `${d.getMonth() + 1}/${d.getDate()}`;
                      }}
                      className="text-xs text-muted-foreground"
                    />
                    <YAxis allowDecimals={false} className="text-xs text-muted-foreground" />
                    <Tooltip
                      labelFormatter={(label) => `Date: ${label}`}
                      formatter={(val: number) => [`${val} Posts`, "Content"]}
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        borderColor: "hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="count"
                      stroke="#f43f5e"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#postGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link href="/admin/users" className="group">
          <Card className="transition-colors hover:border-indigo-500/50 hover:bg-muted/40">
            <CardContent className="flex items-center justify-between p-5">
              <div className="space-y-1">
                <p className="font-semibold text-foreground">User Management</p>
                <p className="text-xs text-muted-foreground">Search, suspend, role changes</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
            </CardContent>
          </Card>
        </Link>

        <Link href="/admin/content" className="group">
          <Card className="transition-colors hover:border-indigo-500/50 hover:bg-muted/40">
            <CardContent className="flex items-center justify-between p-5">
              <div className="space-y-1">
                <p className="font-semibold text-foreground">Content Moderation</p>
                <p className="text-xs text-muted-foreground">Posts, comments, bulk actions</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
            </CardContent>
          </Card>
        </Link>

        <Link href="/admin/moderation" className="group">
          <Card className="transition-colors hover:border-indigo-500/50 hover:bg-muted/40">
            <CardContent className="flex items-center justify-between p-5">
              <div className="space-y-1">
                <p className="font-semibold text-foreground">Moderation Queue</p>
                <p className="text-xs text-muted-foreground">AI scores, severity reviews</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
            </CardContent>
          </Card>
        </Link>

        <Link href="/admin/activity" className="group">
          <Card className="transition-colors hover:border-indigo-500/50 hover:bg-muted/40">
            <CardContent className="flex items-center justify-between p-5">
              <div className="space-y-1">
                <p className="font-semibold text-foreground">Activity Audit Logs</p>
                <p className="text-xs text-muted-foreground">Immutable admin audit trails</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
