"use client";

import { RiskBadge } from "@/components/risk-badge";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, readable } from "@/features/events/event-utils";
import type { PlanAction } from "@/lib/api/types";

// ─── Status colour tokens ─────────────────────────────────────────────────────

const STATUS_RING: Record<string, string> = {
  completed: "ring-2 ring-emerald-400",
  running: "ring-2 ring-indigo-400 animate-pulse",
  failed: "ring-2 ring-red-400",
  waiting_approval: "ring-2 ring-amber-400",
  cancelled: "ring-2 ring-slate-300",
  rolled_back: "ring-2 ring-slate-300",
};

function ringClass(status: string): string {
  return STATUS_RING[status] ?? "ring-1 ring-slate-200";
}

// ─── Connector arrow between dependent steps ──────────────────────────────────

function DependencyArrow() {
  return (
    <div className="flex items-center justify-center py-1" aria-hidden>
      <svg className="h-5 w-5 text-slate-300" fill="none" viewBox="0 0 20 20">
        <path
          d="M10 3v10m0 0-3-3m3 3 3-3"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
        />
      </svg>
    </div>
  );
}

// ─── Individual step card ─────────────────────────────────────────────────────

function StepCard({
  action,
  index,
  names,
}: {
  action: PlanAction;
  index: number;
  names: Map<string, string>;
}) {
  const stepLabel = `Step ${index + 1}`;
  const dependsLabels = action.depends_on?.length
    ? action.depends_on.map((id) => names.get(id) ?? "a previous step").join(", ")
    : null;
  const resultSummary =
    typeof action.execution_result?.summary === "string"
      ? action.execution_result.summary
      : null;
  const subscriptionResults = Array.isArray(action.execution_result?.subscriptions)
    ? action.execution_result.subscriptions.filter(
        (item): item is Record<string, unknown> =>
          typeof item === "object" && item !== null && typeof item.service === "string",
      )
    : [];

  return (
    <Card className={`transition-shadow duration-150 ${ringClass(action.status)}`}>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              {stepLabel}
            </span>
            <CardTitle className="text-base capitalize">
              {readable(action.action_type.split(".").at(-1) ?? action.action_type)}
            </CardTitle>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={action.status} />
            <RiskBadge risk={action.risk_level} />
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <dl className="divide-y divide-slate-100 text-sm">
          <DescRow label="App" value={readable(action.connector)} />
          <DescRow
            label="Your approval"
            value={
              action.requires_approval
                ? "Required before this step runs"
                : "Not needed — your settings allow this"
            }
          />
          {action.policy_reason && <DescRow label="Why" value={readable(action.policy_reason)} />}
          {dependsLabels && <DescRow label="Runs after" value={dependsLabels} />}
          {action.completed_at && (
            <DescRow
              label="Finished"
              value={<time dateTime={action.completed_at}>{formatDate(action.completed_at)}</time>}
            />
          )}
          {resultSummary && (
            <DescRow
              label="Result"
              value={
                <div className="space-y-2">
                  <p>{resultSummary}</p>
                  {subscriptionResults.length ? (
                    <ul className="list-disc space-y-1 pl-4">
                      {subscriptionResults.map((item, resultIndex) => (
                        <li key={`${String(item.service)}-${resultIndex}`}>
                          <span className="font-medium">{String(item.service)}</span>
                          {typeof item.subject === "string" ? ` — ${item.subject}` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              }
            />
          )}
          {action.last_error && <DescRow label="Problem" value={action.last_error} error />}
        </dl>
      </CardContent>
    </Card>
  );
}

function DescRow({
  label,
  value,
  error = false,
}: {
  label: string;
  value: React.ReactNode;
  error?: boolean;
}) {
  return (
    <div className="grid grid-cols-[8rem_1fr] gap-2 py-2 first:pt-0 last:pb-0">
      <dt className={`font-medium ${error ? "text-red-600" : "text-slate-500"}`}>{label}</dt>
      <dd className={error ? "text-red-600" : "text-slate-800"}>{value}</dd>
    </div>
  );
}

// ─── DAG layout: group by topological depth ───────────────────────────────────

function buildLevels(actions: PlanAction[]): PlanAction[][] {
  const idToIndex = new Map(actions.map((a, i) => [a.id, i]));
  const depth = new Array<number>(actions.length).fill(0);

  // Simple topological depth: each action's depth = max(dep depths) + 1
  for (let i = 0; i < actions.length; i++) {
    const deps = actions[i].depends_on ?? [];
    for (const depId of deps) {
      const di = idToIndex.get(depId);
      if (di !== undefined) {
        depth[i] = Math.max(depth[i], depth[di] + 1);
      }
    }
  }

  const maxDepth = Math.max(...depth, 0);
  const levels: PlanAction[][] = Array.from({ length: maxDepth + 1 }, () => []);
  actions.forEach((a, i) => levels[depth[i]].push(a));
  return levels;
}

// ─── Public component ─────────────────────────────────────────────────────────

export function ActionDag({ actions }: { actions: PlanAction[] }) {
  if (!actions.length) return null;

  const names = new Map(actions.map((a, i) => [a.id, `Step ${i + 1}`]));
  const levels = buildLevels(actions);

  return (
    <section aria-labelledby="action-dag-title">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-950" id="action-dag-title">
          Steps FlowPilot will take
        </h2>
        <p className="text-sm text-slate-600">
          Steps at the same level can run in parallel. Each level waits for the level above it to
          finish.
        </p>
      </div>

      <div className="space-y-2">
        {levels.map((levelActions, levelIndex) => (
          <div key={levelIndex}>
            {/* Arrow connector between levels */}
            {levelIndex > 0 && <DependencyArrow />}

            {/* Level label */}
            {levels.length > 1 && (
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                {levelIndex === 0 ? "Starts immediately" : `After level ${levelIndex}`}
              </p>
            )}

            {/* Cards in this level */}
            <div className={`grid gap-3 ${levelActions.length > 1 ? "md:grid-cols-2" : ""}`}>
              {levelActions.map((action) => (
                <StepCard
                  key={action.id}
                  action={action}
                  index={actions.indexOf(action)}
                  names={names}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
