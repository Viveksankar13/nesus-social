"use client";

import type { LucideIcon } from "lucide-react";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import React, { useRef } from "react";
import { cn } from "@/lib/utils";

const TILT_MAX = 8;
const TILT_SPRING = { stiffness: 300, damping: 28 } as const;
const GLOW_SPRING = { stiffness: 180, damping: 22 } as const;

export interface SpotlightFeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  color?: string;
  dimmed?: boolean;
  onHoverStart?: () => void;
  onHoverEnd?: () => void;
  className?: string;
}

export function SpotlightFeatureCard({
  icon: Icon,
  title,
  description,
  color = "#6366f1",
  dimmed = false,
  onHoverStart,
  onHoverEnd,
  className,
}: SpotlightFeatureCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useReducedMotion();
  const [isActive, setIsActive] = React.useState(false);
  const resetTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const normX = useMotionValue(0.5);
  const normY = useMotionValue(0.5);

  const rawRotateX = useTransform(normY, [0, 1], [TILT_MAX, -TILT_MAX]);
  const rawRotateY = useTransform(normX, [0, 1], [-TILT_MAX, TILT_MAX]);

  const rotateX = useSpring(rawRotateX, TILT_SPRING);
  const rotateY = useSpring(rawRotateY, TILT_SPRING);
  const glowOpacity = useSpring(0, GLOW_SPRING);

  const updateCoordinates = (clientX: number, clientY: number) => {
    const el = cardRef.current;
    if (!el || prefersReducedMotion) return;
    const rect = el.getBoundingClientRect();
    const clampedX = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const clampedY = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
    normX.set(clampedX);
    normY.set(clampedY);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    updateCoordinates(e.clientX, e.clientY);
  };

  const handleMouseEnter = () => {
    if (prefersReducedMotion) return;
    if (resetTimeoutRef.current) clearTimeout(resetTimeoutRef.current);
    setIsActive(true);
    glowOpacity.set(1);
    onHoverStart?.();
  };

  const handleMouseLeave = () => {
    normX.set(0.5);
    normY.set(0.5);
    glowOpacity.set(0);
    setIsActive(false);
    onHoverEnd?.();
  };

  // Touch device support for mobile and tablets
  const handleTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    if (prefersReducedMotion || !e.touches[0]) return;
    if (resetTimeoutRef.current) clearTimeout(resetTimeoutRef.current);
    setIsActive(true);
    glowOpacity.set(1);
    onHoverStart?.();
    updateCoordinates(e.touches[0].clientX, e.touches[0].clientY);
  };

  const handleTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
    if (prefersReducedMotion || !e.touches[0]) return;
    updateCoordinates(e.touches[0].clientX, e.touches[0].clientY);
  };

  const handleTouchEnd = () => {
    normX.set(0.5);
    normY.set(0.5);
    glowOpacity.set(0);
    // Smooth reset timeout after tap release
    resetTimeoutRef.current = setTimeout(() => {
      setIsActive(false);
      onHoverEnd?.();
    }, 600);
  };

  React.useEffect(() => {
    return () => {
      if (resetTimeoutRef.current) clearTimeout(resetTimeoutRef.current);
    };
  }, []);

  return (
    <motion.div
      ref={cardRef}
      animate={{
        scale: dimmed ? 0.96 : 1,
        opacity: dimmed ? 0.55 : 1,
      }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseMove={handleMouseMove}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleTouchEnd}
      style={{
        rotateX,
        rotateY,
        transformPerspective: 900,
        touchAction: "pan-y",
      }}
      className={cn(
        "group relative flex flex-col gap-4 overflow-hidden rounded-2xl border p-6 text-left select-none",
        // Theme backgrounds & borders
        "border-border/60 bg-card/85 backdrop-blur-md shadow-sm transition-[border-color,box-shadow] duration-300",
        "hover:border-primary/40 hover:shadow-lg dark:hover:border-primary/50",
        isActive && "border-primary/40 shadow-lg dark:border-primary/50",
        className
      )}
    >
      {/* Static ambient accent glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-2xl transition-opacity duration-300"
        style={{
          background: `radial-gradient(ellipse at 20% 20%, ${color}15, transparent 70%)`,
        }}
      />

      {/* Dynamic hover/touch spotlight glow layer */}
      <motion.div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-2xl"
        style={{
          opacity: glowOpacity,
          background: `radial-gradient(ellipse at 25% 25%, ${color}35, transparent 65%)`,
        }}
      />

      {/* Shimmer sweep effect (hover and touch active) */}
      <div
        aria-hidden="true"
        className={cn(
          "pointer-events-none absolute inset-y-0 left-0 w-[50%] -translate-x-full -skew-x-12 bg-gradient-to-r from-transparent via-white/10 dark:via-white/5 to-transparent transition-transform duration-700 ease-out group-hover:translate-x-[300%]",
          isActive && "translate-x-[300%]"
        )}
      />

      {/* Icon badge */}
      <div
        className={cn(
          "relative z-10 flex h-12 w-12 items-center justify-center rounded-xl transition-transform duration-300 group-hover:scale-105",
          isActive && "scale-105"
        )}
        style={{
          background: `${color}18`,
          boxShadow: `inset 0 0 0 1px ${color}35`,
        }}
      >
        <Icon className="h-6 w-6" style={{ color }} />
      </div>

      {/* Title & Description */}
      <div className="relative z-10 flex flex-col gap-2">
        <h3
          className={cn(
            "text-lg font-bold text-foreground tracking-tight transition-colors group-hover:text-primary",
            isActive && "text-primary"
          )}
        >
          {title}
        </h3>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {description}
        </p>
      </div>

      {/* Accent animated bottom line */}
      <div
        aria-hidden="true"
        className={cn(
          "absolute bottom-0 left-0 h-[2.5px] w-0 rounded-full transition-all duration-500 group-hover:w-full",
          isActive && "w-full"
        )}
        style={{
          background: `linear-gradient(to right, ${color}, transparent)`,
        }}
      />
    </motion.div>
  );
}

