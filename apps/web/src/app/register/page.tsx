"use client";

import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

export default function RegisterPage() {
  const { register, user, loading } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/");
  }, [loading, user, router]);

  if (loading || user) {
    return (
      <div className="min-h-screen app-shell flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-accent animate-spin" />
      </div>
    );
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password, name);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen app-shell flex flex-col">
      <div className="flex justify-end p-4">
        <ThemeToggle />
      </div>
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-6">
          <div className="text-center">
            <h1 className="text-lg font-semibold text-primary tracking-tight">JobReach</h1>
            <p className="text-sm text-muted mt-1">Create your account</p>
          </div>

          <form onSubmit={onSubmit} className="auth-card p-6 space-y-4">
            {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
            <Field label="Name">
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-field" placeholder="Your name" />
            </Field>
            <Field label="Email">
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" />
            </Field>
            <Field label="Password">
              <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" placeholder="At least 8 characters" />
            </Field>
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 btn-primary disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Create account
            </button>
          </form>

          <p className="text-center text-sm text-muted">
            Already have an account?{" "}
            <Link href="/login" className="text-accent hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-muted mb-1.5">{label}</label>
      {children}
    </div>
  );
}
