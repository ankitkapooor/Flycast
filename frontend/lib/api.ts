import { BrainInfo, DemoItem, ExperimentStatus, FullExperimentResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function getHealth(): Promise<{ status: string; brain_loaded: boolean; runtime_neurons?: number }> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Healthcheck failed: ${res.statusText}`);
  }
  return res.json();
}

export async function getBrainInfo(): Promise<BrainInfo> {
  const res = await fetch(`${API_BASE}/api/v1/brain`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Brain info fetch failed: ${res.statusText}`);
  }
  return res.json();
}

export async function getDemos(): Promise<DemoItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/demos`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Demos fetch failed: ${res.statusText}`);
  }
  const data = await res.json();
  return data.demos;
}

export async function getDemoCsv(demoId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/demos/${demoId}/csv`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load demo CSV: ${res.statusText}`);
  }
  return res.text();
}

export async function submitExperiment(formData: FormData): Promise<{ id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/v1/experiments`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Experiment submission failed (${res.status})`);
  }
  return res.json();
}

export async function getExperimentStatus(id: string): Promise<ExperimentStatus> {
  const res = await fetch(`${API_BASE}/api/v1/experiments/${id}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to poll status: ${res.statusText}`);
  }
  return res.json();
}

export async function getExperimentResults(id: string): Promise<FullExperimentResponse> {
  const res = await fetch(`${API_BASE}/api/v1/experiments/${id}/results`, { cache: "no-store" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Failed to fetch results (${res.status})`);
  }
  return res.json();
}

export function getPredictionsCsvUrl(id: string): string {
  return `${API_BASE}/api/v1/experiments/${id}/predictions.csv`;
}

export function getExperimentJsonUrl(id: string): string {
  return `${API_BASE}/api/v1/experiments/${id}/experiment.json`;
}
