"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

type StatusState = "loading" | "success" | "error" | "missing_token";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { toast } = useToast();

  const [status, setStatus] = React.useState<StatusState>("loading");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [resendEmail, setResendEmail] = React.useState("");
  const [isResending, setIsResending] = React.useState(false);
  const [resendSent, setResendSent] = React.useState(false);

  React.useEffect(() => {
    if (!token) {
      setStatus("missing_token");
      return;
    }

    let isMounted = true;

    async function verify() {
      try {
        await apiClient.get(`/auth/verify-email?token=${encodeURIComponent(token as string)}`);
        if (isMounted) {
          setStatus("success");
        }
      } catch (err: unknown) {
        if (isMounted) {
          setStatus("error");
          const msg =
            err instanceof Error
              ? err.message
              : "Verification token is invalid or has expired.";
          setErrorMessage(msg);
        }
      }
    }

    verify();

    return () => {
      isMounted = false;
    };
  }, [token]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resendEmail) return;

    setIsResending(true);
    try {
      await apiClient.post("/auth/resend-verification", { email: resendEmail });
      setResendSent(true);
      toast({
        title: "Link dispatched",
        description: "If an unverified account exists, a new email was sent.",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to send link.";
      toast({
        title: "Error",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setIsResending(false);
    }
  };

  if (status === "loading") {
    return (
      <Card className="border shadow-lg text-center p-6">
        <CardContent className="flex flex-col items-center justify-center space-y-4 pt-6">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <h2 className="text-xl font-bold">Verifying your email...</h2>
          <p className="text-sm text-muted-foreground">
            Please wait while we confirm your verification token.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (status === "success") {
    return (
      <Card className="border shadow-lg text-center">
        <CardHeader className="space-y-3 pb-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <CardTitle className="text-2xl font-bold">Email Verified!</CardTitle>
          <CardDescription className="text-base text-muted-foreground">
            Your Nexus Social account is now active and ready to use.
          </CardDescription>
        </CardHeader>
        <CardFooter className="pt-2">
          <Link href="/login" className="w-full">
            <Button className="w-full">Proceed to Sign In</Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="border shadow-lg">
      <CardHeader className="space-y-2 text-center pb-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <XCircle className="h-7 w-7" />
        </div>
        <CardTitle className="text-2xl font-bold">Verification Failed</CardTitle>
        <CardDescription>
          {errorMessage || "The verification link is invalid, incomplete, or has already expired."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-2">
        {resendSent ? (
          <div className="rounded-md bg-emerald-500/15 p-3 text-sm text-emerald-600 dark:text-emerald-400 text-center">
            If your email is registered and unverified, a new verification link has been sent!
          </div>
        ) : (
          <form onSubmit={handleResend} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="resend_email">Request New Verification Link</Label>
              <Input
                id="resend_email"
                type="email"
                placeholder="your-email@example.com"
                value={resendEmail}
                onChange={(e) => setResendEmail(e.target.value)}
                required
                disabled={isResending}
              />
            </div>
            <Button
              type="submit"
              variant="outline"
              className="w-full"
              disabled={isResending || !resendEmail}
            >
              {isResending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sending...
                </>
              ) : (
                "Resend Verification Email"
              )}
            </Button>
          </form>
        )}
      </CardContent>
      <CardFooter className="flex justify-center pt-2">
        <Link href="/login" className="text-sm text-primary hover:underline font-medium">
          Back to Sign In
        </Link>
      </CardFooter>
    </Card>
  );
}

export default function VerifyEmailPage() {
  return (
    <React.Suspense
      fallback={
        <Card className="border shadow-lg p-12 text-center flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </Card>
      }
    >
      <VerifyEmailContent />
    </React.Suspense>
  );
}
