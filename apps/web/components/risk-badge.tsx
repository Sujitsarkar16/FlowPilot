import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";

import type { RiskLevel } from "@/lib/contracts";
import { cn } from "@/lib/utils";

const riskDisplay: Record<
  RiskLevel,
  { Icon: typeof ShieldAlert; label: string; className: string }
> = {
  green: {
    Icon: ShieldCheck,
    label: "Low risk",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  yellow: {
    Icon: ShieldQuestion,
    label: "Review required",
    className: "border-amber-200 bg-amber-50 text-amber-800",
  },
  red: {
    Icon: ShieldAlert,
    label: "High risk",
    className: "border-red-200 bg-red-50 text-red-800",
  },
};

export function RiskBadge({ className, risk }: { className?: string; risk: RiskLevel }) {
  const { Icon, label, className: tone } = riskDisplay[risk];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        tone,
        className,
      )}
    >
      <Icon aria-hidden="true" size={14} />
      {label}
    </span>
  );
}
