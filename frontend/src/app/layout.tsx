import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

const appName = process.env.NEXT_PUBLIC_APP_NAME ?? "Nexus Social";

export const metadata: Metadata = {
  title: {
    default: appName,
    template: `%s | ${appName}`,
  },
  description: "Connect, share, and discover with AI-powered social features.",
  keywords: ["social media", "AI", "community", "posts", "connect"],
  authors: [{ name: "Nexus Social Team" }],
  creator: "Nexus Social",
  icons: {
    icon: "/drupal.png",
    apple: "/drupal.png",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    title: appName,
    description: "Connect, share, and discover with AI-powered social features.",
    siteName: appName,
  },
  twitter: {
    card: "summary_large_image",
    title: appName,
    description: "Connect, share, and discover with AI-powered social features.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#6366f1" },
    { media: "(prefers-color-scheme: dark)", color: "#1e1b4b" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
        suppressHydrationWarning
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
