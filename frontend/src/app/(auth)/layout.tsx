/**
 * Auth Layout — wraps login, register, verify, forgot/reset password pages.
 * Full implementation in Stage 7. Placeholder for scaffold.
 */

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Brand header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-brand-gradient mb-3 shadow-lg shadow-brand-500/30">
            <span className="text-2xl">🌐</span>
          </div>
          <h1 className="text-2xl font-bold text-gradient">Nexus Social</h1>
        </div>
        {children}
      </div>
    </div>
  );
}
