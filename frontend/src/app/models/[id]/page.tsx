import Link from "next/link";
import { api } from "../../../lib/api";
import { AlertBadge } from "../../../components/AlertBadge";
import { GateStatus } from "../../../components/GateStatus";

export const dynamic = "force-dynamic";

interface Props {
  params: { id: string };
}

export default async function ModelDetailPage({ params }: Props) {
  const [model, compliance, alerts] = await Promise.all([
    api.models.get(params.id).catch(() => null),
    api.models.compliance(params.id).catch(() => null),
    api.alerts.list(params.id).catch(() => []),
  ]);

  if (!model) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Model not found</div>
      </main>
    );
  }

  const gates = compliance?.governance_gate_status
    ? [
        { name: "Fairness", passed: compliance.governance_gate_status.fairness_gate_passed },
        { name: "Robustness", passed: compliance.governance_gate_status.robustness_gate_passed },
        { name: "Explainability", passed: compliance.governance_gate_status.explainability_gate_passed },
        { name: "Documentation", passed: compliance.governance_gate_status.documentation_gate_passed },
      ]
    : [];

  const overallAlert =
    compliance && compliance.open_action_alerts > 0
      ? "action"
      : compliance && compliance.fairness_alert_count > 0
      ? "watch"
      : "none";

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href="/models" className="text-blue-600 hover:underline text-sm">← Models</Link>
          <h1 className="text-xl font-bold text-gray-900">{model.name}</h1>
          <span className="text-sm text-gray-500">v{model.version}</span>
          <AlertBadge level={overallAlert} />
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Model info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            ["Risk Tier", `Tier ${model.risk_tier}`],
            ["Status", model.validation_status],
            ["Fairness Alerts", compliance?.fairness_alert_count ?? "—"],
            ["Doc Completeness", compliance?.latest_completeness_score != null
              ? `${(compliance.latest_completeness_score * 100).toFixed(0)}%`
              : "N/A"],
          ].map(([label, value]) => (
            <div key={String(label)} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
              <div className="text-xs text-gray-500">{label}</div>
              <div className="text-lg font-semibold text-gray-800 mt-1">{String(value)}</div>
            </div>
          ))}
        </div>

        {/* Governance gates */}
        {gates.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <h2 className="font-semibold text-gray-800 mb-3">Governance Gates</h2>
            <GateStatus
              gates={gates}
              promotionBlocked={compliance?.governance_gate_status?.promotion_blocked ?? false}
            />
          </div>
        )}

        {/* Active alerts */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b bg-gray-50">
            <h2 className="font-semibold text-gray-800">Active Alerts</h2>
          </div>
          {alerts.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-sm">No open alerts</div>
          ) : (
            <div className="divide-y">
              {alerts.map((alert) => (
                <div key={alert.id} className="px-5 py-3 flex items-start gap-3">
                  <AlertBadge level={alert.alert_level as "action" | "watch"} />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-800">{alert.alert_type}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{alert.message}</div>
                  </div>
                  {alert.hitl_required && (
                    <Link href="/alerts" className="text-xs text-blue-600 hover:underline whitespace-nowrap">
                      Approve →
                    </Link>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* MLflow info */}
        {model.mlflow_run_id && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm text-sm">
            <h2 className="font-semibold text-gray-800 mb-2">MLflow</h2>
            <div className="font-mono text-gray-600">Run ID: {model.mlflow_run_id}</div>
            <a
              href={`http://localhost:5000/#/experiments/0/runs/${model.mlflow_run_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline text-xs mt-1 block"
            >
              Open in MLflow UI →
            </a>
          </div>
        )}
      </div>
    </main>
  );
}
