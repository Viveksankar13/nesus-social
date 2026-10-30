"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2, XCircle } from "lucide-react";

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

const resetPasswordSchema = z
  .object({
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must include at least one uppercase letter")
      .regex(/[a-z]/, "Must include at least one lowercase letter")
      .regex(/[0-9]/, "Must include at least one number")
      .regex(
        /[!@#$%^&*(),.?":{}|<>_]/,
        "Must include at least one special character"
      ),
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { toast } = useToast();

  const [showPassword, setShowPassword] = React.useState(false);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const [isSuccess, setIsSuccess] = React.useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirm_password: "" },
  });

  const passwordValue = watch("password", "");

  const passwordChecks = [
    { label: "8+ characters", met: passwordValue.length >= 8 },
    { label: "Uppercase letter", met: /[A-Z]/.test(passwordValue) },
    { label: "Lowercase letter", met: /[a-z]/.test(passwordValue) },
    { label: "Number", met: /[0-9]/.test(passwordValue) },
    {
      label: "Special character",
      met: /[!@#$%^&*(),.?":{}|<>_]/.test(passwordValue),
    },
  ];

  if (!token) {
    return (
      <Card className="border shadow-lg text-center">
        <CardHeader className="space-y-3 pb-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <XCircle className="h-8 w-8" />
          </div>
          <CardTitle className="text-2xl font-bold">Invalid Link</CardTitle>
          <CardDescription>
            This password reset link is missing a valid token.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex justify-center pt-2">
          <Link href="/forgot-password">
            <Button variant="outline">Request New Link</Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  const onSubmit = async (data: ResetPasswordFormValues) => {
    setErrorMsg(null);
    try {
      await apiClient.post("/auth/reset-password", {
        token,
        new_password: data.password,
      });

      setIsSuccess(true);
      toast({
        title: "Password updated!",
        description: "You can now sign in with your new password.",
      });

      setTimeout(() => {
        router.push("/login");
      }, 2500);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to reset password. The link may have expired.";
      setErrorMsg(message);
    }
  };

  if (isSuccess) {
    return (
      <Card className="border shadow-lg text-center">
        <CardHeader className="space-y-3 pb-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <CardTitle className="text-2xl font-bold">Password Reset!</CardTitle>
          <CardDescription>
            Your password has been changed successfully. Redirecting you to sign in...
          </CardDescription>
        </CardHeader>
        <CardFooter className="pt-2">
          <Link href="/login" className="w-full">
            <Button className="w-full">Sign In Now</Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="border shadow-lg">
      <CardHeader className="space-y-1">
        <div className="flex items-center space-x-2 text-primary pb-1">
          <KeyRound className="h-5 w-5" />
          <span className="text-xs font-bold uppercase tracking-wider">New Password</span>
        </div>
        <CardTitle className="text-2xl font-bold tracking-tight">Set New Password</CardTitle>
        <CardDescription>
          Choose a strong password to secure your account
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {errorMsg && (
            <div className="rounded-md bg-destructive/15 border border-destructive/20 p-3 text-sm text-destructive">
              {errorMsg}
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="password">New Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                autoComplete="new-password"
                disabled={isSubmitting}
                className="pr-10"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.password && (
              <p className="text-xs text-destructive">{errors.password.message}</p>
            )}

            <div className="grid grid-cols-2 gap-1.5 pt-1 text-xs">
              {passwordChecks.map((item, idx) => (
                <div
                  key={idx}
                  className={`flex items-center space-x-1.5 ${
                    item.met ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"
                  }`}
                >
                  {item.met ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40 shrink-0 ml-1 mr-1" />
                  )}
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="confirm_password">Confirm New Password</Label>
            <Input
              id="confirm_password"
              type="password"
              placeholder="••••••••"
              autoComplete="new-password"
              disabled={isSubmitting}
              {...register("confirm_password")}
            />
            {errors.confirm_password && (
              <p className="text-xs text-destructive">{errors.confirm_password.message}</p>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Updating password...
              </>
            ) : (
              "Save New Password"
            )}
          </Button>

          <Link href="/login" className="text-sm text-muted-foreground hover:text-foreground text-center">
            Back to Sign In
          </Link>
        </CardFooter>
      </form>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <React.Suspense
      fallback={
        <Card className="border shadow-lg p-12 text-center flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </Card>
      }
    >
      <ResetPasswordContent />
    </React.Suspense>
  );
}
