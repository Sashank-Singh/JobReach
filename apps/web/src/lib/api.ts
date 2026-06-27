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
  skill?: string;
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

export interface SalaryEstimate {
  estimated: boolean;
  min_salary?: number;
  max_salary?: number;
  currency: string;
  period: string;
  sample_size: number;
  message: string;
}

export interface ApplicationDetail {
  id: string;
  job_id: string;
  status: string;
  applied_at: string;
  interview_date?: string;
  pipeline_order: number;
  notes?: string;
  job?: { id: string; title: string; company_name: string };
}

export interface SkillInfo {
  id: string;
  name: string;
  category?: string;
}

export interface Analytics {
  total_jobs: number;
  total_companies: number;
  avg_match_score?: number;
  skills_demand: { skill: string; count: number }[];
  salary_by_experience: { level: string; avg_min: number; avg_max: number; count: number }[];
  remote_job_pct: number;
  visa_sponsorship_pct: number;
  top_hiring_companies: { name: string; slug: string; active_jobs: number }[];
  jobs_by_source: { source: string; count: number }[];
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

  getSimilarJobs: (jobId: string) =>
    fetchApi<Job[]>(`/api/v1/jobs/${jobId}/similar`),

  getSalaryEstimate: (jobId: string) =>
    fetchApi<SalaryEstimate>(`/api/v1/jobs/${jobId}/salary-estimate`),

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

  getApplications: () => fetchApi<ApplicationDetail[]>("/api/v1/me/applications"),

  updateApplication: (appId: string, body: Partial<{ status: string; interview_date: string; pipeline_order: number; notes: string }>) =>
    fetchApi<ApplicationDetail>(`/api/v1/applications/${appId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  getNotifications: () => fetchApi<Notification[]>("/api/v1/notifications"),

  triggerDigest: () => fetchApi("/api/v1/notifications/digest", { method: "POST" }),

  getFilters: () => fetchApi<{ id: string; name: string; filters: Record<string, string> }[]>("/api/v1/filters"),

  getSkills: (category?: string, search?: string) => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (search) params.set("search", search);
    return fetchApi<SkillInfo[]>(`/api/v1/skills?${params}`);
  },

  getSkillCategories: () =>
    fetchApi<{ category: string; count: number }[]>("/api/v1/skills/categories"),

  getAnalytics: () =>
    fetchApi<Analytics>("/api/v1/analytics"),
};

export type { AuthUser };
