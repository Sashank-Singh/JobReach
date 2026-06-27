"use client";

import { useAuth } from "@/lib/auth-context";
import { JobDashboard } from "@/components/job-dashboard";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="h-screen app-shell flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-accent animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  return <JobDashboard />;
}
