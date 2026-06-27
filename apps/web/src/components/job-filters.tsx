"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { JobFilters } from "@/lib/api";
import { useEffect, useState } from "react";

interface Props {
  filters: JobFilters;
  onChange: (filters: JobFilters) => void;
}

export function JobFiltersPanel({ filters, onChange }: Props) {
  const [keyword, setKeyword] = useState(filters.keyword || "");

  useEffect(() => {
    setKeyword(filters.keyword || "");
  }, [filters.keyword]);

  useEffect(() => {
    const timer = setTimeout(() => {
      onChange({ ...filters, keyword: keyword || undefined, page: 1 });
    }, 350);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce keyword only
  }, [keyword]);

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
          placeholder="e.g. AI engineer stripe remote"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="w-full pl-9 pr-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        />
        <p className="text-[10px] text-zinc-600 mt-1">Multi-word search · title & description</p>
      </div>

      <Field label="Location">
        <input
          type="text"
          placeholder="Country, city, or remote..."
          value={filters.location || ""}
          onChange={(e) => update("location", e.target.value)}
          className="input-field"
        />
        <p className="text-[10px] text-zinc-600 mt-1">Try: United States, Ireland, Singapore, remote</p>
      </Field>

      <Field label="Company">
        <input
          type="text"
          placeholder="stripe, openai..."
          value={filters.company || ""}
          onChange={(e) => update("company", e.target.value)}
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
