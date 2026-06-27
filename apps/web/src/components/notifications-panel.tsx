"use client";

import { Bell } from "lucide-react";
import { jobApi, Notification } from "@/lib/api";
import { useEffect, useState } from "react";

export function NotificationsPanel() {
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    jobApi.getNotifications().then(setItems).catch(() => setItems([])).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const runDigest = async () => {
    await jobApi.triggerDigest();
    load();
  };

  return (
    <div className="p-4 border-t border-default">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs font-medium text-secondary">
          <Bell className="w-3.5 h-3.5" />
          Job alerts
        </div>
        <button onClick={runDigest} className="text-xs text-accent hover:underline">
          Refresh
        </button>
      </div>
      {loading ? (
        <p className="text-xs text-muted">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-xs text-muted">No alerts yet</p>
      ) : (
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {items.slice(0, 3).map((n, i) => (
            <div key={i} className="text-xs p-2.5 rounded-md bg-surface border border-default">
              <p className="text-primary font-medium">{n.title}</p>
              <p className="text-muted mt-0.5 whitespace-pre-line leading-relaxed">{n.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
