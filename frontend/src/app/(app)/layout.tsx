"use client";

import * as React from "react";
import { Navbar } from "@/components/layout/navbar";
import { Sidebar, MobileSectionFooter } from "@/components/layout/sidebar";
import { AIChatWidget } from "@/components/ai/ai-chat-widget";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <div className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 flex flex-col md:flex-row">
        <Sidebar />
        <main className="flex-1 min-w-0 py-6">{children}</main>
      </div>
      <MobileSectionFooter />
      <AIChatWidget />
    </div>
  );
}
