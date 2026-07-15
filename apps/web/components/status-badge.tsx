import type { ActionResultStatus, ActionStatus, ApprovalStatus, PlanStatus } from "@/lib/contracts";
import { cn } from "@/lib/utils";

type StatusValue =
  | PlanStatus
  | ActionStatus
  | ApprovalStatus
  | ActionResultStatus
  | "connected"
  | "error"
  | "revoked";
type Tone = "emerald" | "amber" | "red" | "slate" | "sky";

const labels: Record<StatusValue, [string, Tone]> = {
  draft: ["Draft", "slate"],
  policy_checked: ["Policy checked", "sky"],
  running: ["Running", "sky"],
  waiting_approval: ["Awaiting approval", "amber"],
  completed: ["Completed", "emerald"],
  partially_completed: ["Partially completed", "amber"],
  failed: ["Failed", "red"],
  cancelled: ["Cancelled", "slate"],
  planned: ["Planned", "slate"],
  blocked: ["Blocked", "red"],
  approved: ["Approved", "emerald"],
  queued: ["Queued", "sky"],
  rolled_back: ["Rolled back", "slate"],
  not_required: ["No approval required", "slate"],
  pending: ["Approval pending", "amber"],
  rejected: ["Rejected", "red"],
  verified: ["Verified", "emerald"],
  connected: ["Connected", "emerald"],
  error: ["Needs attention", "red"],
  revoked: ["Disconnected", "slate"],
};

const tones: Record<Tone, string> = {
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-800",
  amber: "border-amber-200 bg-amber-50 text-amber-800",
  red: "border-red-200 bg-red-50 text-red-800",
  slate: "border-slate-200 bg-slate-50 text-slate-700",
  sky: "border-sky-200 bg-sky-50 text-sky-800",
};

export function StatusBadge({
  className,
  status,
}: {
  className?: string;
  status: StatusValue | string;
}) {
  const [label, tone] = labels[status as StatusValue] ?? [status.replaceAll("_", " "), "slate"];
  return (
    <span
      aria-label={`Status: ${label}`}
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        tones[tone as Tone],
        className,
      )}
    >
      {label}
    </span>
  );
}
