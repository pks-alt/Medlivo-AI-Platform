const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export type DashboardSummary = {
  submission_ready: number;
  interested_replies: number;
  jobs_at_risk: number;
  active_matching_jobs: number;
  qualified_today: number;
};

export type JobListItem = {
  id: string;
  source_job_id: string;
  title: string;
  division: string;
  customer: string;
  location: string;
  status: string;
  strong_matches: number;
  submission_ready: number;
  start_date: string | null;
};

export async function getDashboard(): Promise<DashboardSummary> {
  const response = await fetch(`${API_URL}/api/v1/dashboard`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load dashboard");
  return response.json();
}

export async function getJobs(): Promise<JobListItem[]> {
  const response = await fetch(`${API_URL}/api/v1/jobs`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load jobs");
  return response.json();
}
