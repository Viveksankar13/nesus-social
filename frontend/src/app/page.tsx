/**
 * Landing Page (Temporary — Stage 0 Scaffold)
 * --------------------------------------------
 * Full landing page UI is built in Stage 7.
 * This placeholder confirms the Next.js app boots correctly.
 */

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-mesh flex items-center justify-center p-8">
      <div className="text-center max-w-2xl mx-auto">
        {/* Brand mark */}
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-brand-gradient mb-8 shadow-lg shadow-brand-500/30">
          <span className="text-4xl">🌐</span>
        </div>

        {/* Headline */}
        <h1 className="text-5xl font-bold mb-4">
          <span className="text-gradient">Nexus Social</span>
        </h1>
        <p className="text-xl text-muted-foreground mb-8">
          AI-Powered Social Media Platform
        </p>

        {/* Status */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-sm font-medium">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          Stage 0 — Scaffold Complete
        </div>

        {/* Stack */}
        <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-muted-foreground">
          {["Next.js 14", "FastAPI", "PostgreSQL", "Gemini AI"].map((tech) => (
            <div
              key={tech}
              className="rounded-lg border border-border bg-card p-3 font-medium"
            >
              {tech}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
