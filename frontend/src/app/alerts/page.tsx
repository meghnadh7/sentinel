"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Alert } from "../../lib/api";
import { AlertBadge } from "../../components/AlertBadge";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [approverName, setApproverName] = useState("");

  useEffect(() => {
    api.alerts.list().then(setAlerts).finally(() => setLoading(false));
  }, []);

  async function handleApprove(alertId: string) {
    const name = approverName || "Dashboard User";
    await api.alerts.approve(alertId, name);
    setAlerts((prev) => prev.map((a) => a.id === alertId ? { ...a, hitl_approved: true, hitl_approved_by: name } : a));
  }

  async function handleReject(alertId: string) {
    const name = approverName || "Dashboard User";
    await api.alerts.reject(alertId, name);
    setAlerts((prev) => prev.map((a) => a.id === alertId ? { ...a, hitl_approved: false, hitl_approved_by: name } : a));
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href="/" className="text-blue-600 hover:underline text-sm">← Dashboard</Link>
          <h1 className="text-xl font-bold text-gray-900">Active Alerts & HITL Approval</h1>
        </div>
      </header>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-4 flex items-center gap-3">
          <input
            type="text"
            placeholder="Your name (for approvals)"
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={approverName}
            onChange={(e) => setApproverName(e.target.value)}
          />
        </div>
        {loading ? (
          <div className="text-center text-gray-400 py-12">Loading alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="text-center text-gray-400 py-12">No open alerts</div>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert) => (
              <div key={alert.id} className={`bg-white rounded-xl border shadow-sm p-5 ${
                alert.alert_level === "action" ? "border-red-300" : "border-yellow-300"
              }`}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <AlertBadge level={alert.alert_level as "action" | "watch"} />
                      <span className="text-sm font-semibold text-gray-800">{alert.alert_type}</span>
                      <span className="text-xs text-gray-500">Model: {alert.model_id}</span>
                    </div>
                    <p className="text-sm text-gray-700 mt-1">{alert.message}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                  {alert.hitl_required && alert.hitl_approved === null && (
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => handleApprove(alert.id)}
                        className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 font-medium"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(alert.id)}
                        className="px-3 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 font-medium"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                  {alert.hitl_approved !== null && (
                    <span className={`text-sm font-semibold ml-4 ${alert.hitl_approved ? "text-green-600" : "text-red-600"}`}>
                      {alert.hitl_approved ? "✓ Approved" : "✗ Rejected"}
                      {alert.hitl_approved_by && ` by ${alert.hitl_approved_by}`}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
