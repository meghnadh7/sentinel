const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export interface Model {
  id: string;
  name: string;
  version: string;
  risk_tier: string;
  validation_status: string;
  mlflow_run_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ComplianceStatus {
  model_id: string;
  model_name: string;
  risk_tier: string;
  validation_status: string;
  fairness_alert_count: number;
  open_action_alerts: number;
  latest_completeness_score: number | null;
  governance_gate_status: {
    fairness_gate_passed: boolean | null;
    robustness_gate_passed: boolean | null;
    explainability_gate_passed: boolean | null;
    documentation_gate_passed: boolean | null;
    all_gates_passed: boolean | null;
    promotion_blocked: boolean;
  } | null;
}

export interface Alert {
  id: string;
  model_id: string;
  alert_type: string;
  alert_level: string;
  message: string | null;
  created_at: string;
  hitl_required: boolean;
  hitl_approved: boolean | null;
  hitl_approved_by: string | null;
  resolved_at: string | null;
}

export interface Campaign {
  campaign_id: string;
  model_id: string;
  status: string;
  total_attacks: number;
  successful_attacks: number;
  attack_success_rate: number | null;
  message: string;
}

export const api = {
  models: {
    list: () => apiFetch<{ models: Model[]; total: number }>("/models"),
    get: (id: string) => apiFetch<Model>(`/models/${id}`),
    compliance: (id: string) => apiFetch<ComplianceStatus>(`/models/${id}/compliance`),
  },
  alerts: {
    list: (modelId?: string) =>
      apiFetch<Alert[]>(`/alerts${modelId ? `?model_id=${modelId}` : ""}`),
    approve: (alertId: string, approvedBy: string) =>
      apiFetch(`/alerts/${alertId}/approve`, {
        method: "POST",
        body: JSON.stringify({ approved_by: approvedBy }),
      }),
    reject: (alertId: string, approvedBy: string) =>
      apiFetch(`/alerts/${alertId}/reject`, {
        method: "POST",
        body: JSON.stringify({ approved_by: approvedBy }),
      }),
    resolve: (alertId: string) =>
      apiFetch(`/alerts/${alertId}/resolve`, { method: "POST" }),
  },
  audit: {
    trigger: (modelId: string) =>
      apiFetch(`/audit/${modelId}`, {
        method: "POST",
        body: JSON.stringify({ trigger: "on_demand" }),
      }),
    verifyChain: () => apiFetch("/audit/chain/verify"),
  },
  redTeam: {
    launch: (modelId: string, campaignType = "prompt_injection", nAttacks = 20) =>
      apiFetch<Campaign>("/red-team/campaign", {
        method: "POST",
        body: JSON.stringify({ model_id: modelId, campaign_type: campaignType, n_attacks: nAttacks }),
      }),
    campaigns: (modelId: string) =>
      apiFetch<Campaign[]>(`/red-team/campaigns/${modelId}`),
  },
};
