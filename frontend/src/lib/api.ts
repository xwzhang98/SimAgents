import type { SettingsData, ParametersData, Message, ProfileInfo, ProfileDetail } from "./types";

const API_BASE = "http://localhost:8000";

export async function uploadFile(file: File): Promise<{ file_id: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startExtraction(params: {
  file_id?: string | null;
  user_parameters?: Record<string, unknown> | null;
  target_software?: string | null;
  custom_prompt?: string | null;
}): Promise<{ session_id: string }> {
  const res = await fetch(`${API_BASE}/api/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function respondToQuestion(sessionId: string, answers: Record<string, unknown>): Promise<void> {
  const res = await fetch(`${API_BASE}/api/respond/${sessionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function getSettings(): Promise<SettingsData> {
  const res = await fetch(`${API_BASE}/api/settings`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateSettings(data: Partial<SettingsData>): Promise<SettingsData> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getParameters(sessionId: string): Promise<ParametersData> {
  const res = await fetch(`${API_BASE}/api/parameters/${sessionId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateParameters(sessionId: string, data: { sections?: Record<string, Record<string, unknown>> }): Promise<ParametersData> {
  const res = await fetch(`${API_BASE}/api/parameters/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getExportUrl(sessionId: string): string {
  return `${API_BASE}/api/parameters/${sessionId}/export`;
}

export function getStreamUrl(sessionId: string): string {
  return `${API_BASE}/api/stream/${sessionId}`;
}

export async function getSessionStatus(): Promise<{ status: string | null; session_id: string | null; messages: Message[]; parameters: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/api/session/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getProfiles(): Promise<ProfileInfo[]> {
  const res = await fetch(`${API_BASE}/api/profiles`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getProfile(software: string): Promise<ProfileDetail> {
  const res = await fetch(`${API_BASE}/api/profiles/${software}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
