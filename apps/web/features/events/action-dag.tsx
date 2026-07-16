import { RiskBadge } from "@/components/risk-badge";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { readable } from "@/features/events/event-utils";
import type { PlanAction } from "@/lib/api/types";

export function ActionDag({ actions }: { actions: PlanAction[] }) {
  const names = new Map(actions.map((action, index) => [action.id, `Action ${index + 1}`]));
  return <section aria-labelledby="action-dag-title"><div className="mb-3"><h2 className="text-lg font-semibold text-slate-950" id="action-dag-title">Action manifest</h2><p className="text-sm text-slate-600">Read-only dependency cards adapt to every screen; this ordered list is the equivalent accessible graph.</p></div>
    <ol className="grid gap-3 md:grid-cols-2" aria-label="Planned actions in dependency order">
      {actions.map((action, index) => <li key={action.id}><Card className="h-full"><CardHeader className="pb-3"><div className="flex flex-wrap items-start justify-between gap-2"><CardTitle className="text-base">{index + 1}. {readable(action.action_type)}</CardTitle><div className="flex gap-2"><StatusBadge status={action.status} /><RiskBadge risk={action.risk_level} /></div></div></CardHeader><CardContent className="space-y-2 text-sm text-slate-600"><p>Connector: {action.connector}</p><p>{action.requires_approval ? "Requires explicit approval." : "May run under the active policy."}</p>{action.policy_reason ? <p>Why: {readable(action.policy_reason)}</p> : null}{action.last_error ? <p className="text-red-700">Retry reason: {action.last_error}</p> : null}<p>Depends on: {action.depends_on?.length ? action.depends_on.map((id) => names.get(id) ?? "an unavailable action").join(", ") : "No earlier actions"}</p></CardContent></Card></li>)}
    </ol>
  </section>;
}
