"use client";

import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface FairnessData {
  protected_class: string;
  demographic_parity_ratio: number | null;
  alert_level: string;
}

interface FairnessChartProps {
  data: FairnessData[];
  threshold?: number;
}

export function FairnessChart({ data, threshold = 0.80 }: FairnessChartProps) {
  const chartData = data.map((d) => ({
    name: d.protected_class,
    ratio: d.demographic_parity_ratio ?? 0,
    alert: d.alert_level,
  }));

  const getColor = (ratio: number, alert: string) => {
    if (alert === "action") return "#ef4444";
    if (alert === "watch") return "#f59e0b";
    return "#22c55e";
  };

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis domain={[0, 1.2]} tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value: number) => [value.toFixed(3), "DP Ratio"]}
          labelFormatter={(label) => `Protected class: ${label}`}
        />
        <ReferenceLine y={threshold} stroke="#ef4444" strokeDasharray="4 4" label={{ value: `Threshold (${threshold})`, position: "right", fontSize: 11 }} />
        <ReferenceLine y={0.85} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "Watch (0.85)", position: "right", fontSize: 11 }} />
        <Bar dataKey="ratio" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, idx) => (
            <Cell key={idx} fill={getColor(entry.ratio, entry.alert)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
