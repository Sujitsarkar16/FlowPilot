"use client";

import { useCallback, useEffect, useState } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { RiskBadge } from "@/components/risk-badge";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { Approval, ApprovalDecision } from "@/lib/api/types";

export function ApprovalsManager() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [target, setTarget] = useState<{ approval: Approval; decision: ApprovalDecision } | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setApprovals(await api.listPendingApprovals()); } catch (caught) { setError(caught); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const decide = async () => {
    if (!target) return;
    setBusy(target.approval.id); setError(null);
    try {
      const updated = target.decision === "approved"
        ? await api.approveApproval(target.approval.id)
        : await api.rejectApproval(target.approval.id);
      setApprovals((current) => current.filter((approval) => approval.id !== updated.id));
      setTarget(null);
    } catch (caught) { setError(caught); } finally { setBusy(null); }
  };

  return <div className="mx-auto max-w-5xl p-4 pb-24 sm:p-6 md:pb-8">
    <header className="mb-6 max-w-3xl"><h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Approvals</h1><p className="mt-2 text-sm leading-6 text-slate-600">Review the action, its risk, and the data it needs before FlowPilot continues.</p></header>
    {error ? <ErrorState className="mb-4" error={error} title="Approval action failed" /> : null}
    {loading ? <LoadingSkeleton className="h-48" label="Loading pending approvals" /> : approvals.length === 0 ? <EmptyState title="No approvals waiting" description="Actions that need your explicit approval will be listed here." /> : <section aria-label="Pending approvals" className="space-y-4">{approvals.map((approval) => <ApprovalCard approval={approval} busy={busy === approval.id} key={approval.id} onDecide={(decision) => setTarget({ approval, decision })} />)}</section>}
    <ConfirmDialog busy={busy === target?.approval.id} confirmLabel={target?.decision === "approved" ? "Approve action" : "Reject action"} description={target ? confirmationDescription(target.approval, target.decision) : ""} destructive={target?.approval.action.risk_level === "red" || target?.decision === "rejected"} onCancel={() => setTarget(null)} onConfirm={() => void decide()} open={target !== null} title={target?.approval.action.risk_level === "red" ? "Confirm high-risk action" : target?.decision === "approved" ? "Approve this action?" : "Reject this action?"} />
  </div>;
}

function ApprovalCard({ approval, busy, onDecide }: { approval: Approval; busy: boolean; onDecide: (decision: ApprovalDecision) => void }) {
  const { action } = approval;
  const accessed = Object.keys(action.input);
  return <Card><CardHeader><div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle className="text-lg">{action.action_type.replace(/[._]/g, " ")}</CardTitle><p className="mt-1 text-sm text-slate-600">Uses {action.connector} · expires {new Date(approval.expires_at).toLocaleString()}</p></div><div className="flex items-center gap-2"><StatusBadge status={action.status} /><RiskBadge risk={action.risk_level} /></div></div></CardHeader><CardContent className="space-y-4"><dl className="grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-medium text-slate-900">Why this needs approval</dt><dd className="mt-1 text-slate-600">{(action.policy_reason ?? "approval required").replaceAll("_", " ")}</dd></div><div><dt className="font-medium text-slate-900">Data accessed</dt><dd className="mt-1 text-slate-600">{accessed.length ? accessed.join(", ") : "No additional fields"}</dd></div><div className="sm:col-span-2"><dt className="font-medium text-slate-900">Consequence</dt><dd className="mt-1 text-slate-600">FlowPilot will queue this action only after approval and completed dependencies.</dd></div></dl><div className="flex flex-wrap justify-end gap-2"><Button disabled={busy} onClick={() => onDecide("rejected")} type="button" variant="outline">Reject</Button><Button disabled={busy} onClick={() => onDecide("approved")} type="button">Approve</Button></div></CardContent></Card>;
}

function confirmationDescription(approval: Approval, decision: ApprovalDecision) {
  const action = approval.action.action_type.replace(/[._]/g, " ");
  if (decision === "rejected") return `Reject ${action}. It will be cancelled and cannot run.`;
  return approval.action.risk_level === "red"
    ? `This high-risk action will be queued after you approve it. Review the data and consequence above carefully.`
    : `Approve ${action}. It will be queued only when its dependencies are complete.`;
}
