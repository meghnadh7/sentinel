"use client";

import Link from "next/link";
import { AlertBadge } from "./AlertBadge";
import { GateStatus } from "./GateStatus";
import type { ComplianceStatus } from "../lib/api";

interface ModelCardProps {
  status: ComplianceStatus;
}

const RISK_TIER_COLORS: Record<string, string> = {
  I: "bg-blue-50 text-blue-700 border-blue-200",
  II: "bg-yellow-50 text-yellow-700 border-yellow-200",
  III: "bg-orange-50 text-orange-700 border-orange-200",
  IV: "bg-red-50 text-red-700 border-red-200",
};

export function ModelCard({ status }: ModelCardProps) {
  const alertLevel =
    status.open_action_alerts > 0
      ? "action"
      : status.fairness_alert_count > 0
      ? "watch"
      : "none";

  const gates = status.governance_gate_status
    ? [
        { name: "Fairness", passed: status.governance_gate_status.fairness_gate_passed },
        { name: "Robustness", passed: status.governance_gate_status.robustness_gate_passed },
        { name: "Explainability", passed: status.governance_gate_status.explainability_gate_passed },
        { name: "Documentation", passed: status.governance_gate_status.documentation_gate_passed },
      ]
    : [];

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <Link
            href={`/models/${status.model_id}`}
            className="text-base font-semibold text-blue-700 hover:underline"
          >
            {status.model_name}
          </Link>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-xs px-2 py-0.5 rounded border font-medium ${RISK_TIER_COLORS[status.risk_tier] ?? ""}`}>
              Tier {status.risk_tier}
            </span>
            <span className="text-xs text-gray-500">{status.validation_status}</span>
          </div>
        </div>
        <AlertBadge level={alertLevel} count={status.open_action_alerts} />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
        <div className="bg-gray-50 rounded-lg p-2">
          <div className="text-gray-500 text-xs">Fairness Alerts</div>
          <div className={`font-semibold text-lg ${status.fairness_alert_count > 0 ? "text-red-600" : "text-green-600"}`}>
            {status.fairness_alert_count}
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-2">
          <div className="text-gray-500 text-xs">Doc Completeness</div>
          <div className={`font-semibold text-lg ${
            status.latest_completeness_score === null
              ? "text-gray-400"
              : status.latest_completeness_score >= 0.9
              ? "text-green-600"
              : "text-yellow-600"
          }`}>
            {status.latest_completeness_score !== null
              ? `${(status.latest_completeness_score * 100).toFixed(0)}%`
              : "N/A"}
          </div>
        </div>
      </div>

      {gates.length > 0 && (
        <div className="border-t border-gray-100 pt-3">
          <div className="text-xs text-gray-500 mb-1.5 font-medium uppercase tracking-wide">
            Governance Gates
          </div>
          <GateStatus
            gates={gates}
            promotionBlocked={status.governance_gate_status?.promotion_blocked ?? false}
          />
        </div>
      )}
    </div>
  );
}
