"use client";

interface AuditEntry {
  id: string;
  agent_name: string;
  action: string;
  timestamp: string;
  current_hash: string;
  previous_hash: string;
}

interface AuditTimelineProps {
  entries: AuditEntry[];
  chainValid: boolean;
}

const AGENT_COLORS: Record<string, string> = {
  auditor: "bg-blue-500",
  red_team: "bg-red-500",
  explainer: "bg-purple-500",
  documenter: "bg-green-500",
  api: "bg-gray-500",
  crew: "bg-indigo-500",
};

export function AuditTimeline({ entries, chainValid }: AuditTimelineProps) {
  return (
    <div>
      <div className={`mb-3 text-sm font-medium px-3 py-1.5 rounded-lg inline-flex items-center gap-2 ${
        chainValid
          ? "bg-green-50 text-green-700 border border-green-200"
          : "bg-red-50 text-red-700 border border-red-200"
      }`}>
        {chainValid ? "✓ Chain Intact" : "✗ Chain Compromised"}
      </div>
      <div className="space-y-3">
        {entries.map((entry, idx) => (
          <div key={entry.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full mt-1 ${AGENT_COLORS[entry.agent_name] ?? "bg-gray-400"}`} />
              {idx < entries.length - 1 && <div className="w-0.5 h-full bg-gray-200 mt-1" />}
            </div>
            <div className="pb-3 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-700">{entry.agent_name}</span>
                <span className="text-xs text-gray-500">{entry.action}</span>
              </div>
              <div className="text-xs text-gray-400 mt-0.5">
                {new Date(entry.timestamp).toLocaleString()}
              </div>
              <div className="font-mono text-[10px] text-gray-400 mt-1 truncate">
                #{entry.current_hash.slice(0, 16)}...
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
