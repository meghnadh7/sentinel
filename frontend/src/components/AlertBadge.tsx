"use client";

interface AlertBadgeProps {
  level: "watch" | "action" | "none";
  count?: number;
}

export function AlertBadge({ level, count }: AlertBadgeProps) {
  const styles = {
    action: "bg-red-100 text-red-800 border border-red-300",
    watch: "bg-yellow-100 text-yellow-800 border border-yellow-300",
    none: "bg-green-100 text-green-800 border border-green-300",
  };
  const labels = { action: "ACTION", watch: "WATCH", none: "OK" };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${styles[level]}`}>
      {level === "action" && <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />}
      {labels[level]}
      {count !== undefined && count > 0 && <span>({count})</span>}
    </span>
  );
}
