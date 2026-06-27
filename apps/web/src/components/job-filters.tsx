"use client";

import { Search } from "lucide-react";
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
    <div className="flex-1 space-y-4 p-4 overflow-y-auto">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">Search & filters</p>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          type="text"
          placeholder="Role, company, keyword…"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="input-field !pl-10"
        />
      </div>

      <Field label="Location">
        <input
          type="text"
          placeholder="City, country, or remote"
          value={filters.location || ""}
          onChange={(e) => update("location", e.target.value)}
          className="input-field"
        />
      </Field>

      <Field label="Company">
        <input
          type="text"
          placeholder="e.g. stripe, notion"
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
          <option value="">Any level</option>
          <option value="entry">Entry</option>
          <option value="mid">Mid</option>
          <option value="senior">Senior</option>
          <option value="staff">Staff+</option>
        </select>
      </Field>

      <Field label="Skill">
        <input
          type="text"
          placeholder="e.g. Python, React, AWS"
          value={filters.skill || ""}
          onChange={(e) => update("skill", e.target.value || undefined)}
          className="input-field"
        />
      </Field>

      <Field label="Work arrangement">
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

      <Field label="Posted">
        <select
          value={filters.posted_days?.toString() || ""}
          onChange={(e) => update("posted_days", e.target.value ? Number(e.target.value) : undefined)}
          className="input-field"
        >
          <option value="">Any time</option>
          <option value="1">Last 24 hours</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
        </select>
      </Field>

      <label className="flex items-center gap-2 text-sm text-secondary cursor-pointer">
        <input
          type="checkbox"
          checked={filters.visa || false}
          onChange={(e) => update("visa", e.target.checked || undefined)}
          className="rounded border-default"
        />
        Visa sponsorship
      </label>
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
