"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Campaign } from "../../lib/api";

const DEMO_MODELS = [
  { id: "model-advisor-v2", name: "AdvisorMatcher_v2" },
  { id: "model-fraud-v1", name: "FraudRiskScorer_v1" },
  { id: "model-halo-rag-v1", name: "HaloAdvisorRAG_v1" },
];

export default function RedTeamPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [launching, setLaunching] = useState(false);
  const [selectedModel, setSelectedModel] = useState(DEMO_MODELS[2].id);
  const [nAttacks, setNAttacks] = useState(10);

  async function loadCampaigns() {
    const all = await Promise.all(
      DEMO_MODELS.map((m) => api.redTeam.campaigns(m.id).catch(() => []))
    );
    setCampaigns(all.flat());
  }

  useEffect(() => { loadCampaigns(); }, []);

  async function launch() {
    setLaunching(true);
    try {
      await api.redTeam.launch(selectedModel, "prompt_injection", nAttacks);
      await loadCampaigns();
    } catch (e) {
      alert("Failed to launch campaign: " + e);
    } finally {
      setLaunching(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href="/" className="text-blue-600 hover:underline text-sm">← Dashboard</Link>
          <h1 className="text-xl font-bold text-gray-900">Red Team Campaigns</h1>
        </div>
      </header>
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Launch form */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Launch New Campaign</h2>
          <div className="flex gap-3 items-end flex-wrap">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Target Model</label>
              <select
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {DEMO_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Attacks</label>
              <input
                type="number"
                min={1}
                max={100}
                value={nAttacks}
                onChange={(e) => setNAttacks(Number(e.target.value))}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-20"
              />
            </div>
            <button
              onClick={launch}
              disabled={launching}
              className="px-4 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 font-medium disabled:opacity-50"
            >
              {launching ? "Launching..." : "Launch Prompt Injection Campaign"}
            </button>
          </div>
        </div>

        {/* Campaign results */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b bg-gray-50">
            <h2 className="font-semibold text-gray-800">Campaign History</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600">Model</th>
                <th className="text-left px-4 py-3 text-gray-600">Status</th>
                <th className="text-left px-4 py-3 text-gray-600">Attacks</th>
                <th className="text-left px-4 py-3 text-gray-600">Success Rate</th>
                <th className="text-left px-4 py-3 text-gray-600">Pass</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {campaigns.map((c) => (
                <tr key={c.campaign_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{c.model_id}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      c.status === "completed" ? "bg-green-100 text-green-700" :
                      c.status === "running" ? "bg-blue-100 text-blue-700" :
                      c.status === "budget_exceeded" ? "bg-yellow-100 text-yellow-700" :
                      "bg-red-100 text-red-700"
                    }`}>{c.status}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{c.total_attacks}</td>
                  <td className="px-4 py-3">
                    {c.attack_success_rate !== null ? (
                      <span className={`font-semibold ${c.attack_success_rate > 0.10 ? "text-red-600" : "text-green-600"}`}>
                        {(c.attack_success_rate * 100).toFixed(1)}%
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {c.attack_success_rate !== null ? (
                      c.attack_success_rate <= 0.10
                        ? <span className="text-green-600 font-bold">✓</span>
                        : <span className="text-red-600 font-bold">✗</span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
              {campaigns.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-10 text-gray-400">No campaigns yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
