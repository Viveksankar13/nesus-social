"use client";

import * as React from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { CheckCircle2, Eye, EyeOff, Loader2, Mail } from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
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

const registerSchema = z
  .object({
    username: z
      .string()
      .min(3, "Username must be at least 3 characters")
      .max(30, "Username must be under 30 characters")
      .regex(
        /^[a-zA-Z0-9_]+$/,
        "Username may only contain letters, numbers, and underscores"
      ),
    email: z.string().email("Please enter a valid email address"),
    display_name: z
      .string()
      .min(1, "Display name is required")
      .max(50, "Display name must be under 50 characters"),
    usn: z
      .string()
      .max(50, "Student USN must be under 50 characters")
      .optional()
      .or(z.literal("")),
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

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const [showPassword, setShowPassword] = React.useState(false);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const [registeredEmail, setRegisteredEmail] = React.useState<string | null>(
    null
  );

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: "",
      email: "",
      display_name: "",
      usn: "",
      password: "",
      confirm_password: "",
    },
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

  const onSubmit = async (data: RegisterFormValues) => {
    setErrorMsg(null);
    try {
      await registerUser({
        username: data.username.toLowerCase(),
        email: data.email,
        display_name: data.display_name,
        usn: data.usn?.trim() || undefined,
        password: data.password,
      });
      setRegisteredEmail(data.email);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Registration failed. Please check your inputs and try again.";
      setErrorMsg(message);
    }
  };

  if (registeredEmail) {
    return (
      <Card className="border shadow-lg text-center">
        <CardHeader className="space-y-3 pb-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600">
            <Mail className="h-7 w-7" />
          </div>
          <CardTitle className="text-2xl font-bold">Check your inbox</CardTitle>
          <CardDescription className="text-base text-muted-foreground">
            We sent a verification link to{" "}
            <span className="font-semibold text-foreground">{registeredEmail}</span>.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Click the link in the email to activate your account. If you don&apos;t see
            it in a few moments, check your spam folder.
          </p>
        </CardContent>
        <CardFooter className="flex flex-col space-y-2 pt-2">
          <Link href="/login" className="w-full">
            <Button variant="default" className="w-full">
              Proceed to Sign In
            </Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="border shadow-lg">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold tracking-tight">Create an Account</CardTitle>
        <CardDescription>
          Join Nexus Social and start connecting with precision
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {errorMsg && (
            <div className="rounded-md bg-destructive/15 border border-destructive/20 p-3 text-sm text-destructive">
              {errorMsg}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="display_name">Display Name</Label>
              <Input
                id="display_name"
                placeholder="Jane Doe"
                disabled={isSubmitting}
                {...register("display_name")}
              />
              {errors.display_name && (
                <p className="text-xs text-destructive">{errors.display_name.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                placeholder="janedoe"
                autoCapitalize="none"
                disabled={isSubmitting}
                {...register("username")}
              />
              {errors.username && (
                <p className="text-xs text-destructive">{errors.username.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="usn">Student USN / College ID</Label>
              <span className="text-[11px] text-muted-foreground">University Seat Number</span>
            </div>
            <Input
              id="usn"
              placeholder="e.g. 1MS21CS001"
              autoCapitalize="characters"
              disabled={isSubmitting}
              {...register("usn")}
            />
            {errors.usn && (
              <p className="text-xs text-destructive">{errors.usn.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              placeholder="jane@example.com"
              autoComplete="email"
              disabled={isSubmitting}
              {...register("email")}
            />
            {errors.email && (
              <p className="text-xs text-destructive">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
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

            {/* Password strength checklist */}
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
            <Label htmlFor="confirm_password">Confirm Password</Label>
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

        <CardFooter className="flex flex-col space-y-4 pt-2">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating account...
              </>
            ) : (
              "Create Account"
            )}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="font-semibold text-primary hover:underline">
              Sign In
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
