"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { JobFilters } from "@/lib/api";

interface Props {
  filters: JobFilters;
  onChange: (filters: JobFilters) => void;
}

export function JobFiltersPanel({ filters, onChange }: Props) {
  const update = (key: keyof JobFilters, value: string | boolean | number | undefined) => {
    onChange({ ...filters, [key]: value, page: 1 });
  };

  return (
    <div className="space-y-4 p-4 border-r border-zinc-800 bg-zinc-950 h-full overflow-y-auto">
      <div className="flex items-center gap-2 text-sm font-semibold text-zinc-300">
        <SlidersHorizontal className="w-4 h-4" />
        Filters
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-zinc-500" />
        <input
          type="text"
          placeholder="Keyword, title, company..."
          value={filters.keyword || ""}
          onChange={(e) => update("keyword", e.target.value)}
          className="w-full pl-9 pr-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        />
      </div>

      <Field label="Location">
        <input
          type="text"
          placeholder="San Francisco, Remote..."
          value={filters.location || ""}
          onChange={(e) => update("location", e.target.value)}
          className="input-field"
        />
      </Field>

      <Field label="Experience">
        <select
          value={filters.experience || ""}
          onChange={(e) => update("experience", e.target.value || undefined)}
          className="input-field"
        >
          <option value="">Any</option>
          <option value="entry">Entry</option>
          <option value="mid">Mid</option>
          <option value="senior">Senior</option>
          <option value="staff">Staff+</option>
        </select>
      </Field>

      <Field label="Remote">
        <select
          value={filters.remote || ""}
          onChange={(e) => update("remote", e.target.value || undefined)}
          className="input-field"
        >
          <option value="">Any</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="onsite">On-site</option>
        </select>
      </Field>

      <Field label="Posted within">
        <select
          value={filters.posted_days?.toString() || ""}
          onChange={(e) => update("posted_days", e.target.value ? Number(e.target.value) : undefined)}
          className="input-field"
        >
          <option value="">Any time</option>
          <option value="1">24 hours</option>
          <option value="7">7 days</option>
          <option value="30">30 days</option>
        </select>
      </Field>

      <label className="flex items-center gap-2 text-sm text-zinc-400 cursor-pointer">
        <input
          type="checkbox"
          checked={filters.visa || false}
          onChange={(e) => update("visa", e.target.checked || undefined)}
          className="rounded border-zinc-700 bg-zinc-900 text-emerald-500"
        />
        Visa sponsorship
      </label>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-zinc-500 mb-1">{label}</label>
      {children}
    </div>
  );
}
