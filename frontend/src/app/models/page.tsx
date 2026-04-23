import Link from "next/link";
import { api } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function ModelsPage() {
  let models: Awaited<ReturnType<typeof api.models.list>>["models"] = [];
  try {
    const data = await api.models.list();
    models = data.models;
  } catch {}

  const RISK_TIER_LABELS: Record<string, string> = {
    I: "Low",
    II: "Moderate",
    III: "High",
    IV: "Critical",
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href="/" className="text-blue-600 hover:underline text-sm">← Dashboard</Link>
          <h1 className="text-xl font-bold text-gray-900">Model Registry</h1>
        </div>
      </header>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Name</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Version</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Risk Tier</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Status</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">MLflow Run</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {models.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-blue-700">
                    <Link href={`/models/${m.id}`} className="hover:underline">{m.name}</Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{m.version}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-gray-100 text-gray-700 border border-gray-200 rounded px-2 py-0.5 font-medium">
                      Tier {m.risk_tier} — {RISK_TIER_LABELS[m.risk_tier]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      m.validation_status === "validated" ? "bg-green-100 text-green-700" :
                      m.validation_status === "flagged" ? "bg-red-100 text-red-700" :
                      "bg-yellow-100 text-yellow-700"
                    }`}>
                      {m.validation_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {m.mlflow_run_id ? m.mlflow_run_id.slice(0, 8) + "..." : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/models/${m.id}`} className="text-blue-600 hover:underline text-xs">
                      View audit →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {models.length === 0 && (
            <div className="text-center py-10 text-gray-400">No models registered</div>
          )}
        </div>
      </div>
    </main>
  );
}
