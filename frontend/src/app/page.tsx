import { ModelCard } from "../components/ModelCard";
import { api } from "../lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 30;

async function getDashboardData() {
  try {
    const { models } = await api.models.list();
    const complianceStatuses = await Promise.all(
      models.map((m) => api.models.compliance(m.id).catch(() => null))
    );
    return { models, complianceStatuses: complianceStatuses.filter(Boolean) };
  } catch {
    return { models: [], complianceStatuses: [] };
  }
}

export default async function DashboardPage() {
  const { models, complianceStatuses } = await getDashboardData();

  const totalActionAlerts = complianceStatuses.reduce(
    (sum, s) => sum + (s?.open_action_alerts ?? 0),
    0
  );
  const modelsWithGaps = complianceStatuses.filter(
    (s) => s && s.fairness_alert_count > 0
  ).length;

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              Sentinel — AI Compliance Dashboard
            </h1>
            <p className="text-sm text-gray-500">
              Continuous audit & red-teaming for financial advisory AI
            </p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <a href="/alerts" className="text-blue-600 hover:underline">Alerts</a>
            <a href="/models" className="text-blue-600 hover:underline">Models</a>
            <a href="/red-team" className="text-blue-600 hover:underline">Red Team</a>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Summary bar */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 p-4 text-center shadow-sm">
            <div className="text-3xl font-bold text-gray-900">{models.length}</div>
            <div className="text-sm text-gray-500 mt-1">Registered Models</div>
          </div>
          <div className={`bg-white rounded-xl border p-4 text-center shadow-sm ${totalActionAlerts > 0 ? "border-red-300 bg-red-50" : "border-gray-200"}`}>
            <div className={`text-3xl font-bold ${totalActionAlerts > 0 ? "text-red-700" : "text-gray-900"}`}>
              {totalActionAlerts}
            </div>
            <div className="text-sm text-gray-500 mt-1">Open Action Alerts</div>
          </div>
          <div className={`bg-white rounded-xl border p-4 text-center shadow-sm ${modelsWithGaps > 0 ? "border-yellow-300 bg-yellow-50" : "border-gray-200"}`}>
            <div className={`text-3xl font-bold ${modelsWithGaps > 0 ? "text-yellow-700" : "text-gray-900"}`}>
              {modelsWithGaps}
            </div>
            <div className="text-sm text-gray-500 mt-1">Models with Fairness Gaps</div>
          </div>
        </div>

        {/* Model compliance grid */}
        <h2 className="text-base font-semibold text-gray-700 mb-4">Model Compliance Overview</h2>
        {complianceStatuses.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <div className="text-lg font-medium">No models registered</div>
            <div className="text-sm mt-1">Run <code>make seed</code> to load demo models</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {complianceStatuses.map((status) =>
              status ? <ModelCard key={status.model_id} status={status} /> : null
            )}
          </div>
        )}
      </div>
    </main>
  );
}
