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
  | "boundary_drawn"
  | "rejected";

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
  rejection_reason: string | null;
  fields_edited_by_reviewer: boolean;
  source: "saved_response" | "ai_review";
}

export interface BlacklistEntry {
  id: string;
  document_id: string;
  reason: string;
  flagged_by: string | null;
  created_at: string;
  resolved: boolean;
  resolution: "dismissed" | "document_rejected" | null;
  resolved_by: string | null;
  resolved_at: string | null;
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

export async function analyzeDocument(file: File, useAi: boolean = false): Promise<AnalyzeResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("use_ai", useAi ? "true" : "false");

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Analysis failed");
  }

  return response.json();
}

export interface OcrStatus {
  use_real_ocr_flag: boolean;
  model_available: boolean;
  load_error: string | null;
}

export async function getOcrStatus(): Promise<OcrStatus> {
  const response = await fetch(`${API_BASE_URL}/api/ocr-status`);
  if (!response.ok) throw new Error("Failed to check AI review status");
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

export async function rejectDocument(documentId: string, reason: string): Promise<AnalyzeResult> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to reject document");
  }
  return response.json();
}

export async function updateDocumentFields(
  documentId: string,
  fields: ExtractedField[]
): Promise<AnalyzeResult> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/fields`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to save field corrections");
  }
  return response.json();
}

export async function blacklistDocument(
  documentId: string,
  reason: string,
  flaggedBy?: string
): Promise<BlacklistEntry> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/blacklist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason, flagged_by: flaggedBy }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Flag failed");
  }
  return response.json();
}

export async function listBlacklist(resolved?: boolean): Promise<BlacklistEntry[]> {
  const qs = resolved !== undefined ? `?resolved=${resolved}` : "";
  const response = await fetch(`${API_BASE_URL}/api/blacklist${qs}`);
  if (!response.ok) throw new Error("Failed to list blacklist entries");
  const body = await response.json();
  return body.entries;
}

export async function resolveBlacklistEntry(
  entryId: string,
  resolution: "dismissed" | "document_rejected",
  resolvedBy?: string
): Promise<BlacklistEntry> {
  const response = await fetch(`${API_BASE_URL}/api/blacklist/${entryId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolution, resolved_by: resolvedBy }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Resolve failed");
  }
  return response.json();
}
