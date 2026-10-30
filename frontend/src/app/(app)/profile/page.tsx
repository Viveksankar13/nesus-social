"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { Loader2 } from "lucide-react";

export default function ProfileRedirectPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!isLoading) {
      if (user?.username) {
        router.replace(`/profile/${user.username}`);
      } else {
        router.replace("/login");
      }
    }
  }, [user, isLoading, router]);

  return (
    <div className="flex h-[50vh] items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm">Loading your profile...</p>
      </div>
    </div>
  );
}
