"use client";

import * as React from "react";
import { Navbar } from "@/components/layout/navbar";
import { Sidebar } from "@/components/layout/sidebar";
import { AIChatWidget } from "@/components/ai/ai-chat-widget";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <div className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 flex">
        <Sidebar />
        <main className="flex-1 min-w-0 py-6 pb-[calc(5.5rem+env(safe-area-inset-bottom,0px))] md:pb-6">{children}</main>
      </div>
      <AIChatWidget />
    </div>
  );
}
