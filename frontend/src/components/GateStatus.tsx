"use client";

interface Gate {
  name: string;
  passed: boolean | null;
}

interface GateStatusProps {
  gates: Gate[];
  promotionBlocked: boolean;
}

export function GateStatus({ gates, promotionBlocked }: GateStatusProps) {
  return (
    <div className="space-y-1">
      {gates.map((gate) => (
        <div key={gate.name} className="flex items-center gap-2 text-sm">
          {gate.passed === null ? (
            <span className="text-gray-400">—</span>
          ) : gate.passed ? (
            <span className="text-green-600 font-bold">✓</span>
          ) : (
            <span className="text-red-600 font-bold">✗</span>
          )}
          <span className={gate.passed === false ? "text-red-700 font-medium" : "text-gray-700"}>
            {gate.name}
          </span>
        </div>
      ))}
      {promotionBlocked && (
        <div className="mt-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">
          Promotion blocked — resolve failed gates before deployment
        </div>
      )}
    </div>
  );
}
