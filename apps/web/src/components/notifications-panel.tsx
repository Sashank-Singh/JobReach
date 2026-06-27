"use client";

import { jobApi, Notification } from "@/lib/api";
import { Bell } from "lucide-react";
import { useEffect, useState } from "react";

export function NotificationsPanel() {
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    jobApi.getNotifications().then(setItems).catch(() => setItems([])).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const runDigest = async () => {
    await jobApi.triggerDigest();
    load();
  };

  return (
    <div className="p-3 border-t border-zinc-800">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
          <Bell className="w-3.5 h-3.5" />
          Alerts
        </div>
        <button onClick={runDigest} className="text-[10px] text-emerald-400 hover:underline">
          Run digest
        </button>
      </div>
      {loading ? (
        <p className="text-xs text-zinc-600">Loading...</p>
      ) : items.length === 0 ? (
        <p className="text-xs text-zinc-600">No alerts yet</p>
      ) : (
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {items.slice(0, 3).map((n, i) => (
            <div key={i} className="text-[10px] p-2 rounded bg-zinc-900 border border-zinc-800">
              <p className="text-zinc-300 font-medium">{n.title}</p>
              <p className="text-zinc-500 mt-0.5 whitespace-pre-line">{n.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
