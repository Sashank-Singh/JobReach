import { AuthUser, getStoredToken } from "./auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Job {
  id: string;
  title: string;
  company: { id: string; name: string; slug: string; logo_url?: string };
  department?: string;
  experience_level?: string;
  remote_type?: string;
  visa_sponsorship?: boolean;
  locations: { city?: string; state?: string; country?: string; is_remote: boolean }[];
  salary?: { min_salary?: number; max_salary?: number; currency: string; period: string };
  skills: string[];
  posted_at?: string;
  apply_url?: string;
  source: string;
  match_score?: number;
  description?: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
  sorted_by_match?: boolean;
}

export interface JobFilters {
  keyword?: string;
  company?: string;
  location?: string;
  experience?: string;
  remote?: string;
  visa?: boolean;
  posted_days?: number;
  salary_min?: number;
  resume_id?: string;
  page?: number;
  page_size?: number;
}

export interface CompanyProfile {
  id: string;
  name: string;
  slug: string;
  website?: string;
  logo_url?: string;
  hiring_velocity?: number;
  visa_sponsorship?: boolean;
  interview_difficulty?: number;
  employee_count?: number;
  office_locations?: string[];
  active_jobs?: number;
  ats_type?: string;
}

export interface ResumeData {
  id: string;
  filename: string;
  parsed_data: { skills?: string[]; experience?: unknown[]; education?: unknown[]; companies?: string[] };
  created_at: string;
}

export interface Notification {
  title: string;
  body: string;
  job_count: number;
  sent_at: string;
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export const jobApi = {
  listJobs: (filters: JobFilters) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== "") params.set(k, String(v));
    });
    return fetchApi<JobListResponse>(`/api/v1/jobs?${params}`);
  },

  getJob: (id: string) => fetchApi<Job>(`/api/v1/jobs/${id}`),

  saveJob: (jobId: string) =>
    fetchApi(`/api/v1/jobs/${jobId}/save`, { method: "POST" }),

  applyJob: (jobId: string, notes?: string) =>
    fetchApi(`/api/v1/jobs/${jobId}/apply`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  referralHandoff: (jobId: string) =>
    fetchApi<{ job_id: string; user_id: string }>(`/api/v1/jobs/${jobId}/referral-handoff`, {
      method: "POST",
    }),

  getCompany: (id: string) => fetchApi<CompanyProfile>(`/api/v1/companies/${id}`),

  getCompanyBySlug: (slug: string) => fetchApi<CompanyProfile>(`/api/v1/companies/slug/${slug}`),

  uploadResume: async (file: File) => {
    const token = getStoredToken();
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/v1/resume/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) throw new Error("Upload failed");
    return res.json() as Promise<ResumeData>;
  },

  getLatestResume: () => fetchApi<ResumeData | null>("/api/v1/me/resume"),

  getSavedJobs: () => fetchApi<{ job_id: string }[]>("/api/v1/me/saved-jobs"),

  getApplications: () => fetchApi<{ job_id: string; status: string }[]>("/api/v1/me/applications"),

  getNotifications: () => fetchApi<Notification[]>("/api/v1/notifications"),

  triggerDigest: () => fetchApi("/api/v1/notifications/digest", { method: "POST" }),

  getFilters: () => fetchApi<{ id: string; name: string; filters: Record<string, string> }[]>("/api/v1/filters"),
};

export type { AuthUser };
