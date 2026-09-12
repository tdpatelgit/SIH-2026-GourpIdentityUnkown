export interface ExtractedField {
  name: string;
  label: string;
  value: string;
  confidence: number;
}

export type DocumentStatus =
  | "auto_approved"
  | "pending_review"
  | "approved"
  | "boundary_drawn";

export interface AnalyzeResult {
  document_id: string;
  filename: string;
  processed_at: string;
  fields: ExtractedField[];
  overall_confidence: number;
  review_required: boolean;
  status: DocumentStatus;
  boundary: number[][] | null;
  owner_username: string | null;
  plot_id: string | null;
}

export interface GovernmentRecord {
  plot_id: number;
  plot_label: string;
  khata_no: string;
  khasra_no: string;
  survey_no: string;
  owner_name: string;
  area: string;
  mutation: string;
  on_file_since: string;
}

export interface AuthResult {
  username: string;
  token: string;
}

// Use the same hostname the frontend was loaded from, so this works both on
// localhost and when accessed over LAN from another device.
const API_BASE_URL =
  typeof window !== "undefined"
    ? `http://${window.location.hostname}:8067`
    : "http://localhost:8067";

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("auth_token");
  return token ? { "X-Auth-Token": token } : {};
}

export async function signup(username: string, password: string): Promise<AuthResult> {
  const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Sign up failed");
  }
  return response.json();
}

export async function login(username: string, password: string): Promise<AuthResult> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Login failed");
  }
  return response.json();
}

export async function analyzeDocument(file: File): Promise<AnalyzeResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Analysis failed");
  }

  return response.json();
}

export async function listDocuments(opts?: {
  status?: DocumentStatus;
  mine?: boolean;
}): Promise<AnalyzeResult[]> {
  const params = new URLSearchParams();
  if (opts?.status) params.set("status", opts.status);
  if (opts?.mine) params.set("mine", "true");
  const qs = params.toString();
  const response = await fetch(
    `${API_BASE_URL}/api/documents${qs ? `?${qs}` : ""}`,
    { headers: authHeaders() }
  );
  if (!response.ok) throw new Error("Failed to list documents");
  const body = await response.json();
  return body.documents;
}

export async function getDocument(documentId: string): Promise<AnalyzeResult> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}`);
  if (!response.ok) throw new Error("Document not found");
  return response.json();
}

export async function approveDocument(documentId: string): Promise<AnalyzeResult> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/approve`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Approve failed");
  return response.json();
}

export async function saveBoundary(
  documentId: string,
  points: number[][]
): Promise<AnalyzeResult> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/boundary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ points }),
  });
  if (!response.ok) throw new Error("Save boundary failed");
  return response.json();
}

export async function dummyUpload(plotId: number): Promise<AnalyzeResult> {
  const response = await fetch(`${API_BASE_URL}/api/documents/dummy-upload`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ plot_id: plotId }),
  });
  if (!response.ok) throw new Error("Dummy upload failed");
  return response.json();
}

export async function getGovernmentRecord(plotId: string | number): Promise<GovernmentRecord> {
  const response = await fetch(`${API_BASE_URL}/api/government-records/${plotId}`);
  if (!response.ok) throw new Error("Government record not found");
  return response.json();
}
