"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { DictationButton } from "@/components/dictation-button";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { RiskBadge } from "@/components/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { StandingOrder, StandingOrderSimulation } from "@/lib/api/types";

import { SimulationDialog } from "./simulation-dialog";

// Compiling a standing order runs a synchronous AI call on the API. Its worst case is
// three provider attempts (30s each) plus exponential backoff — roughly 94s. The client's
// 15s default would abort first and mislabel a still-running compile as "timed out", so
// these AI-bound mutations get a budget that covers the backend ceiling.
// ponytail: matches today's fixed backend retry budget; if that becomes configurable,
// derive this from the API instead of hardcoding.
const AI_COMPILE_TIMEOUT_MS = 120_000;

// ─── Template library ─────────────────────────────────────────────────────────
// Each template generates a natural-language instruction that the AI compiler
// understands. Users can pick one as a starting point or write from scratch.

interface Template {
  id: string;
  label: string;
  trigger: string; // human-readable trigger label
  triggerKey: string; // matches simulation sample keys
  icon: string;
  description: string;
  instruction: string; // the text sent to the API
}

const TEMPLATES: Template[] = [
  {
    id: "travel-full",
    label: "Travel Autopilot",
    trigger: "Flight / Hotel booked",
    triggerKey: "travel_booked",
    icon: "✈️",
    description: "Trip folder, itinerary, packing list, and a family message waiting for approval.",
    instruction:
      "Whenever I book a flight or hotel, prepare a trip folder with the itinerary, a packing checklist, and a local weather summary. Then draft a message to my family with the travel details and wait for my approval before sending.",
  },
  {
    id: "travel-change",
    label: "Rebooking Alert",
    trigger: "Travel plan changed",
    triggerKey: "travel_changed",
    icon: "🔄",
    description: "Reschedule calendar events and alert me when a flight is rescheduled.",
    instruction:
      "Whenever a flight or hotel booking changes, update my calendar event and send me a summary of what changed so I can review and update any related plans.",
  },
  {
    id: "client-launch",
    label: "Client Launch",
    trigger: "Client confirmed",
    triggerKey: "client_confirmed",
    icon: "🚀",
    description: "GitHub workspace, proposal template, and kickoff checklist on client sign-off.",
    instruction:
      "Whenever a client confirms a project, create a private GitHub repository for the project, prepare a kickoff checklist, and draft a welcome message to the client waiting for my approval before sending.",
  },
  {
    id: "client-lead",
    label: "New Lead Follow-up",
    trigger: "New client lead",
    triggerKey: "client_opportunity",
    icon: "🤝",
    description: "Draft a proposal and add a follow-up reminder when a new lead arrives.",
    instruction:
      "Whenever I receive a new client lead or opportunity, prepare a brief proposal outline and add a follow-up reminder to my calendar within 48 hours.",
  },
  {
    id: "salary",
    label: "Salary Autopilot",
    trigger: "Salary credited",
    triggerKey: "salary_credited",
    icon: "💰",
    description: "Budget allocation summary and overspend warning when salary arrives.",
    instruction:
      "Whenever my salary is credited, calculate the budget allocations (savings, rent, food, discretionary) based on my usual percentages, generate a CSV summary, and warn me if any category is overspent compared to last month.",
  },
  {
    id: "subscription",
    label: "Subscription Guard",
    trigger: "Subscription renewal",
    triggerKey: "subscription_renewal",
    icon: "🔔",
    description: "Alert and cancel option whenever a subscription is about to renew.",
    instruction:
      "Whenever a subscription renewal is detected, notify me with the service name and cost and ask whether I want to keep it or mark it for cancellation.",
  },
];

// ─── Trigger chips shown on compiled order cards ──────────────────────────────

const TRIGGER_LABELS: Record<string, string> = {
  travel_booked: "✈️ Travel booked",
  travel_changed: "🔄 Travel changed",
  client_opportunity: "🤝 New lead",
  client_confirmed: "✅ Client confirmed",
  salary_credited: "💰 Salary",
  subscription_renewal: "🔔 Subscription",
  generic_important_event: "📌 Important event",
};

// ─── Create form ──────────────────────────────────────────────────────────────

function CreateForm({
  busy,
  onCreated,
  onError,
}: {
  busy: boolean;
  onCreated: (order: StandingOrder) => void;
  onError: (err: unknown) => void;
}) {
  const [mode, setMode] = useState<"templates" | "custom">("templates");
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [instruction, setInstruction] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const pickTemplate = (tpl: Template) => {
    setSelectedTemplate(tpl);
    setInstruction(tpl.instruction);
    setMode("custom"); // switch to edit view so user can tweak
    setTimeout(() => textareaRef.current?.focus(), 50);
  };

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!instruction.trim()) return;
    setSubmitting(true);
    try {
      const order = await api.createStandingOrder(
        { instruction: instruction.trim() },
        { timeoutMs: AI_COMPILE_TIMEOUT_MS },
      );
      onCreated(order);
      setInstruction("");
      setSelectedTemplate(null);
      setMode("templates");
    } catch (err) {
      onError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const isSubmitting = busy || submitting;

  return (
    <Card className="mb-6">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Add an automation</CardTitle>
          <div className="flex rounded-lg border border-slate-200 p-0.5 text-sm">
            <button
              className={`rounded-md px-3 py-1 font-medium transition ${
                mode === "templates"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              onClick={() => setMode("templates")}
              type="button"
            >
              Templates
            </button>
            <button
              className={`rounded-md px-3 py-1 font-medium transition ${
                mode === "custom"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              onClick={() => setMode("custom")}
              type="button"
            >
              Write your own
            </button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* ── Template picker ── */}
        {mode === "templates" && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {TEMPLATES.map((tpl) => (
              <button
                className="group flex flex-col gap-2 rounded-xl border border-slate-200 p-4 text-left transition hover:border-indigo-300 hover:bg-indigo-50 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                id={`template-${tpl.id}`}
                key={tpl.id}
                onClick={() => pickTemplate(tpl)}
                type="button"
              >
                <div className="flex items-center gap-2">
                  <span aria-hidden="true" className="text-2xl">
                    {tpl.icon}
                  </span>
                  <span className="font-semibold text-slate-900 group-hover:text-indigo-900">
                    {tpl.label}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-slate-600">{tpl.description}</p>
                <span className="mt-auto inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 group-hover:bg-indigo-100 group-hover:text-indigo-700">
                  Trigger: {tpl.trigger}
                </span>
              </button>
            ))}

            {/* Custom blank tile */}
            <button
              className="group flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 p-4 text-center transition hover:border-indigo-300 hover:bg-indigo-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              onClick={() => {
                setInstruction("");
                setSelectedTemplate(null);
                setMode("custom");
              }}
              type="button"
            >
              <span
                aria-hidden="true"
                className="text-2xl text-slate-400 group-hover:text-indigo-500"
              >
                ✏️
              </span>
              <span className="font-medium text-slate-700 group-hover:text-indigo-800">
                Write from scratch
              </span>
            </button>
          </div>
        )}

        {/* ── Instruction editor ── */}
        {mode === "custom" && (
          <form className="space-y-4" onSubmit={submit}>
            {selectedTemplate && (
              <div className="flex items-center gap-2 rounded-lg bg-indigo-50 px-3 py-2">
                <span aria-hidden="true">{selectedTemplate.icon}</span>
                <span className="text-sm font-medium text-indigo-800">
                  Starting from: {selectedTemplate.label}
                </span>
                <button
                  className="ml-auto text-xs text-indigo-600 hover:underline"
                  onClick={() => {
                    setSelectedTemplate(null);
                    setInstruction("");
                  }}
                  type="button"
                >
                  Clear
                </button>
              </div>
            )}

            <div>
              <label
                className="block text-sm font-medium text-slate-900"
                htmlFor="order-instruction"
              >
                Instruction
              </label>
              <p className="mt-0.5 text-xs text-slate-500">
                Describe the trigger and what FlowPilot should do. Be as specific as you like — the
                AI will compile it into a structured rule.
              </p>
              <textarea
                className="mt-2 min-h-32 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500"
                disabled={isSubmitting}
                id="order-instruction"
                onChange={(e) => setInstruction(e.target.value)}
                placeholder='e.g. "Whenever I book a flight, prepare a packing list and ask before sending a message to my partner."'
                ref={textareaRef}
                required
                value={instruction}
              />
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <DictationButton
                  disabled={isSubmitting}
                  label="automation instruction"
                  onError={onError}
                  onTranscript={(transcript) =>
                    setInstruction((current) =>
                      `${current}${current.trim() ? " " : ""}${transcript}`,
                    )
                  }
                />
              </div>
              <p className="mt-1 text-right text-xs text-slate-400">
                {instruction.length} / 4000 chars
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                className="text-sm text-slate-500 hover:text-slate-700"
                onClick={() => setMode("templates")}
                type="button"
              >
                ← Back to templates
              </button>
              <Button
                disabled={isSubmitting || !instruction.trim()}
                id="save-automation"
                type="submit"
              >
                {isSubmitting ? "Saving…" : "Save automation"}
              </Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Inline edit form ─────────────────────────────────────────────────────────

function InlineEditForm({
  order,
  onSave,
  onCancel,
  busy,
}: {
  order: StandingOrder;
  onSave: (instruction: string) => Promise<void>;
  onCancel: () => void;
  busy: boolean;
}) {
  const [instruction, setInstruction] = useState(order.instruction);
  const [saving, setSaving] = useState(false);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!instruction.trim() || instruction.trim() === order.instruction) {
      onCancel();
      return;
    }
    setSaving(true);
    await onSave(instruction.trim());
    setSaving(false);
  };

  const isSubmitting = busy || saving;

  return (
    <form className="space-y-3" onSubmit={submit}>
      <textarea
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus
        className="min-h-28 w-full rounded-md border border-indigo-300 px-3 py-2 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500"
        disabled={isSubmitting}
        onChange={(e) => setInstruction(e.target.value)}
        required
        value={instruction}
      />
      <div className="flex gap-2">
        <Button disabled={isSubmitting} size="sm" type="submit">
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
        <Button
          disabled={isSubmitting}
          onClick={onCancel}
          size="sm"
          type="button"
          variant="outline"
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ─── Order card ───────────────────────────────────────────────────────────────

function OrderCard({
  busy,
  editing,
  onDelete,
  onEditStart,
  onEditSave,
  onEditCancel,
  onRetry,
  onSimulate,
  onToggle,
  order,
}: {
  busy: boolean;
  editing: boolean;
  onDelete: () => void;
  onEditStart: () => void;
  onEditSave: (instruction: string) => Promise<void>;
  onEditCancel: () => void;
  onRetry: () => void;
  onSimulate: () => void;
  onToggle: () => void;
  order: StandingOrder;
}) {
  const rule = order.compiled_rule;
  const statusLabel = order.enabled
    ? "On"
    : order.compilation_status === "failed"
      ? "Needs attention"
      : order.compilation_status === "pending"
        ? "Compiling…"
        : "Off";

  const statusStyle = order.enabled
    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
    : order.compilation_status === "failed"
      ? "bg-red-50 text-red-700 border-red-200"
      : "bg-slate-100 text-slate-600 border-slate-200";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {editing ? (
              <InlineEditForm
                busy={busy}
                onCancel={onEditCancel}
                onSave={onEditSave}
                order={order}
              />
            ) : (
              <>
                <CardTitle className="leading-snug">{order.instruction}</CardTitle>
                {rule?.explanation && (
                  <p className="mt-1.5 text-sm text-slate-600">{rule.explanation}</p>
                )}
                {!rule && order.last_error && (
                  <p className="mt-1.5 text-sm text-red-600">{order.last_error}</p>
                )}
                {!rule && !order.last_error && (
                  <p className="mt-1.5 text-sm text-slate-400 italic">Setting things up…</p>
                )}
              </>
            )}
          </div>

          {!editing && (
            <span
              className={`flex-shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusStyle}`}
            >
              {statusLabel}
            </span>
          )}
        </div>
      </CardHeader>

      {!editing && (
        <CardContent className="space-y-4">
          {/* Trigger chips */}
          {rule && rule.trigger_event_types.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Triggers when
              </p>
              <div className="flex flex-wrap gap-1.5">
                {rule.trigger_event_types.map((type) => (
                  <span
                    className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-800"
                    key={type}
                  >
                    {TRIGGER_LABELS[type] ?? type.replaceAll("_", " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Action chips */}
          {rule && rule.action_templates.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Actions
              </p>
              <div className="flex flex-wrap gap-1.5">
                {rule.action_templates.map((action) => (
                  <span
                    className="inline-flex items-center gap-1.5 rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs"
                    key={action.action_type}
                  >
                    <span className="text-slate-700">
                      {action.action_type.replace(/[._]/g, " ")}
                    </span>
                    <RiskBadge risk={action.risk_level} />
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {rule && rule.warnings.length > 0 && (
            <ul className="list-disc pl-5 text-sm text-amber-700">
              {rule.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}

          {/* Actions row */}
          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              disabled={busy || order.compilation_status !== "compiled"}
              onClick={onToggle}
              size="sm"
              type="button"
              variant="outline"
            >
              {order.enabled ? "Turn off" : "Turn on"}
            </Button>
            {order.compilation_status === "failed" && (
              <Button disabled={busy} onClick={onRetry} size="sm" type="button" variant="outline">
                Retry compilation
              </Button>
            )}
            <Button
              disabled={busy}
              id={`edit-order-${order.id}`}
              onClick={onEditStart}
              size="sm"
              type="button"
              variant="outline"
            >
              Edit
            </Button>
            <Button
              disabled={busy || !order.enabled || order.compilation_status !== "compiled"}
              id={`simulate-order-${order.id}`}
              onClick={onSimulate}
              size="sm"
              type="button"
              variant="outline"
            >
              Test
            </Button>
            <Button
              className="ml-auto text-red-700 hover:text-red-800"
              disabled={busy}
              id={`delete-order-${order.id}`}
              onClick={onDelete}
              size="sm"
              type="button"
              variant="ghost"
            >
              Delete
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

// ─── Main manager ─────────────────────────────────────────────────────────────

export function StandingOrdersManager() {
  const [orders, setOrders] = useState<StandingOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<StandingOrder | null>(null);
  const [simulationTarget, setSimulationTarget] = useState<StandingOrder | null>(null);
  const [simulation, setSimulation] = useState<StandingOrderSimulation | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setOrders(await api.listStandingOrders());
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreated = (order: StandingOrder) => {
    setOrders((cur) => [...cur, order]);
  };

  const handleToggle = async (order: StandingOrder) => {
    setBusy(order.id);
    setError(null);
    try {
      const updated = await api.updateStandingOrder(order.id, { enabled: !order.enabled });
      setOrders((cur) => cur.map((o) => (o.id === order.id ? updated : o)));
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  };

  const handleCompile = async (order: StandingOrder) => {
    setBusy(order.id);
    setError(null);
    try {
      const updated = await api.compileStandingOrder(order.id, {
        timeoutMs: AI_COMPILE_TIMEOUT_MS,
      });
      setOrders((cur) => cur.map((item) => (item.id === order.id ? updated : item)));
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  };

  const handleEditSave = async (order: StandingOrder, instruction: string) => {
    setBusy(order.id);
    setError(null);
    try {
      const updated = await api.updateStandingOrder(
        order.id,
        { instruction },
        { timeoutMs: AI_COMPILE_TIMEOUT_MS },
      );
      setOrders((cur) => cur.map((o) => (o.id === order.id ? updated : o)));
      setEditingId(null);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setBusy(deleteTarget.id);
    setError(null);
    try {
      await api.deleteStandingOrder(deleteTarget.id);
      setOrders((cur) => cur.filter((o) => o.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  };

  const handleSimulate = async (sampleEvent: string) => {
    if (!simulationTarget) return;
    setBusy(`simulate-${simulationTarget.id}`);
    setError(null);
    try {
      setSimulation(await api.simulateStandingOrder(simulationTarget.id, sampleEvent));
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(null);
    }
  };

  // Find the compiled trigger key for the simulation dialog default sample.
  const simulationTriggerKey =
    simulationTarget?.compiled_rule?.trigger_event_types?.[0] ?? undefined;

  return (
    <div className="mx-auto max-w-5xl p-4 pb-24 sm:p-6 md:pb-8">
      <header className="mb-6 max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
          Automations
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Tell FlowPilot what to do when the same kind of event happens again. It always asks before
          anything risky.
        </p>
      </header>

      <CreateForm busy={busy !== null} onCreated={handleCreated} onError={setError} />

      {error ? (
        <ErrorState className="mb-4" error={error} title="That automation could not be updated" />
      ) : null}

      {loading ? (
        <LoadingSkeleton className="h-48" label="Loading automations" />
      ) : orders.length === 0 ? (
        <EmptyState
          description="Pick a template above or write your own instruction to get started."
          title="No automations yet"
        />
      ) : (
        <section aria-label="Your automations" className="space-y-4">
          <p className="text-sm text-slate-500">
            {orders.length} automation{orders.length !== 1 ? "s" : ""}
          </p>
          {orders.map((order) => (
            <OrderCard
              busy={busy === order.id}
              editing={editingId === order.id}
              key={order.id}
              onDelete={() => setDeleteTarget(order)}
              onEditCancel={() => setEditingId(null)}
              onEditSave={(instruction) => handleEditSave(order, instruction)}
              onEditStart={() => setEditingId(order.id)}
              onRetry={() => void handleCompile(order)}
              onSimulate={() => {
                setSimulationTarget(order);
                setSimulation(null);
              }}
              onToggle={() => void handleToggle(order)}
              order={order}
            />
          ))}
        </section>
      )}

      <SimulationDialog
        busy={busy === `simulate-${simulationTarget?.id}`}
        defaultTrigger={simulationTriggerKey}
        error={error}
        onClose={() => {
          setSimulationTarget(null);
          setSimulation(null);
        }}
        onSubmit={handleSimulate}
        open={simulationTarget !== null}
        result={simulation}
      />

      <ConfirmDialog
        busy={busy === deleteTarget?.id}
        confirmLabel="Delete automation"
        description="This permanently removes the automation. Existing activity and events are not affected."
        destructive
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void handleDelete()}
        open={deleteTarget !== null}
        title="Delete this automation?"
      />
    </div>
  );
}
