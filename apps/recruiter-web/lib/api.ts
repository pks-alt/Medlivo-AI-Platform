import "server-only";

// Runtime server configuration takes precedence over the legacy public setting.
const API_URL = (
  process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"
).replace(/\/+$/, "");

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

async function apiHeaders(): Promise<Headers> {
  const headers = new Headers({ Accept: "application/json" });

  // Local development can use a local API. Cloud Run must authenticate.
  if (!process.env.K_SERVICE) return headers;

  const target = new URL(API_URL);
  if (
    target.protocol !== "https:" ||
    !target.hostname.endsWith(".run.app") ||
    target.username || target.password || target.port ||
    target.pathname !== "/" || target.search || target.hash
  ) {
    throw new Error("API_URL must be the HTTPS root URL of the private Cloud Run API");
  }

  // Use the receiving service's canonical status.url as the token audience.
  const audience = process.env.API_AUTH_AUDIENCE || API_URL;
  const metadataUrl = new URL(
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
  );
  metadataUrl.searchParams.set("audience", audience);

  // The metadata server supplies the attached service account's short-lived
  // identity token. Never place it in a NEXT_PUBLIC variable or send it to clients.
  const tokenResponse = await fetch(metadataUrl, {
    headers: { "Metadata-Flavor": "Google" },
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(5000),
  });
  if (!tokenResponse.ok) {
    throw new Error(`Cloud Run identity token request failed (HTTP ${tokenResponse.status})`);
  }
  const token = (await tokenResponse.text()).trim();
  if (!token || /\s/.test(token)) {
    throw new Error("Cloud Run identity token response was empty or invalid");
  }

  // Leave Authorization available for future application-level authentication.
  headers.set("X-Serverless-Authorization", `Bearer ${token}`);
  return headers;
}

async function getApiJson<T>(path: string, label: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: await apiHeaders(),
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) {
    // Include the status for diagnosis, but never log tokens or response bodies.
    throw new Error(`Failed to load ${label} (API HTTP ${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function getDashboard(): Promise<DashboardSummary> {
  return getApiJson<DashboardSummary>("/api/v1/dashboard", "dashboard");
}

export async function getJobs(): Promise<JobListItem[]> {
  return getApiJson<JobListItem[]>("/api/v1/jobs", "jobs");
}
