"use client";

import * as React from "react";
import { Navbar } from "@/components/layout/navbar";
import { Sidebar, MobileNavBar } from "@/components/layout/sidebar";
import { AIChatWidget } from "@/components/ai/ai-chat-widget";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="max-w-6xl w-full mx-auto px-4 sm:px-6 flex flex-col md:flex-row">
        <Sidebar />
        <main
          className="flex-1 min-w-0 py-6 pb-32 md:pb-8"
          style={{ paddingBottom: "max(8rem, calc(6.5rem + env(safe-area-inset-bottom, 20px)))" }}
        >
          {children}
        </main>
      </div>
      <MobileNavBar />
      <AIChatWidget />
    </div>
  );
}
