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

export const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
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
    fetchApi(`/api/v1/jobs/save`, {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, user_id: DEMO_USER_ID }),
    }),

  applyJob: (jobId: string) =>
    fetchApi(`/api/v1/jobs/apply`, {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, user_id: DEMO_USER_ID }),
    }),

  referralHandoff: (jobId: string) =>
    fetchApi<{ job_id: string; user_id: string }>(`/api/v1/jobs/${jobId}/referral-handoff`, {
      method: "POST",
    }),

  uploadResume: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/v1/resume/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  },
};
