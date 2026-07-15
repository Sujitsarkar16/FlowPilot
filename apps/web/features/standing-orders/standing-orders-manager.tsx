"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { RiskBadge } from "@/components/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { StandingOrder, StandingOrderSimulation } from "@/lib/api/types";

import { SimulationDialog } from "./simulation-dialog";

export function StandingOrdersManager() {
  const [orders, setOrders] = useState<StandingOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<StandingOrder | null>(null);
  const [simulationTarget, setSimulationTarget] = useState<StandingOrder | null>(null);
  const [simulation, setSimulation] = useState<StandingOrderSimulation | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setOrders(await api.listStandingOrders()); } catch (caught) { setError(caught); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!instruction.trim()) return;
    setBusy("create"); setError(null);
    try { const order = await api.createStandingOrder({ instruction: instruction.trim() }); setOrders((current) => [...current, order]); setInstruction(""); }
    catch (caught) { setError(caught); } finally { setBusy(null); }
  };


  const update = async (order: StandingOrder, enabled: boolean) => {
    setBusy(order.id); setError(null);
    try { const updated = await api.updateStandingOrder(order.id, { enabled }); setOrders((current) => current.map((item) => item.id === order.id ? updated : item)); }
    catch (caught) { setError(caught); } finally { setBusy(null); }
  };
  const edit = async (order: StandingOrder) => {
    const instruction = window.prompt("Update this standing order", order.instruction)?.trim();
    if (!instruction || instruction === order.instruction) return;
    setBusy(order.id); setError(null);
    try { const updated = await api.updateStandingOrder(order.id, { instruction }); setOrders((current) => current.map((item) => item.id === order.id ? updated : item)); }
    catch (caught) { setError(caught); } finally { setBusy(null); }
  };
  const remove = async () => {
    if (!deleteTarget) return;
    setBusy(deleteTarget.id); setError(null);
    try { await api.deleteStandingOrder(deleteTarget.id); setOrders((current) => current.filter((item) => item.id !== deleteTarget.id)); setDeleteTarget(null); }
    catch (caught) { setError(caught); } finally { setBusy(null); }
  };
  const simulate = async (sampleEvent: string) => {
    if (!simulationTarget) return;
    setBusy(`simulate-${simulationTarget.id}`); setError(null);
    try { setSimulation(await api.simulateStandingOrder(simulationTarget.id, sampleEvent)); }
    catch (caught) { setError(caught); } finally { setBusy(null); }
  };

  return <div className="mx-auto max-w-5xl p-4 pb-24 sm:p-6 md:pb-8">
    <header className="mb-6 max-w-3xl"><h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Standing Orders</h1><p className="mt-2 text-sm leading-6 text-slate-600">Describe a repeatable intention. PulseOS compiles it into bounded actions, then policy still decides what may run.</p></header>
    <Card className="mb-6"><CardHeader><CardTitle>Create a standing order</CardTitle></CardHeader><CardContent><form className="space-y-3" onSubmit={create}><label className="block text-sm font-medium" htmlFor="standing-order-instruction">What should PulseOS do?</label><textarea className="min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" disabled={busy !== null} id="standing-order-instruction" onChange={(event) => setInstruction(event.target.value)} placeholder="Whenever I book a flight, prepare my trip and ask before informing my family." required value={instruction} /><p className="text-xs text-slate-500">Rules never permit automatic high-risk actions.</p><div className="flex justify-end"><Button disabled={busy !== null} type="submit">{busy === "create" ? "Compiling…" : "Create rule"}</Button></div></form></CardContent></Card>
    {error ? <ErrorState className="mb-4" error={error} title="Standing order action failed" /> : null}
    {loading ? <LoadingSkeleton className="h-48" label="Loading standing orders" /> : orders.length === 0 ? <EmptyState title="No standing orders yet" description="Create a rule for future travel, client, or salary events." /> : <section aria-label="Standing orders" className="space-y-4">{orders.map((order) => <OrderCard busy={busy === order.id} key={order.id} onDelete={() => setDeleteTarget(order)} onEdit={() => void edit(order)} onSimulate={() => { setSimulationTarget(order); setSimulation(null); }} onToggle={() => void update(order, !order.enabled)} order={order} />)}</section>}
    <SimulationDialog busy={busy === `simulate-${simulationTarget?.id}`} error={error} onClose={() => { setSimulationTarget(null); setSimulation(null); }} onSubmit={simulate} open={simulationTarget !== null} result={simulation} />
    <ConfirmDialog busy={busy === deleteTarget?.id} confirmLabel="Delete rule" description="This permanently removes the standing order. Existing event history is unchanged." destructive onCancel={() => setDeleteTarget(null)} onConfirm={() => void remove()} open={deleteTarget !== null} title="Delete this standing order?" />
  </div>;
}


function OrderCard({ busy, onDelete, onEdit, onSimulate, onToggle, order }: { busy: boolean; onDelete: () => void; onEdit: () => void; onSimulate: () => void; onToggle: () => void; order: StandingOrder }) {
  const rule = order.compiled_rule;
  return <Card><CardHeader><div className="flex items-start justify-between gap-4"><div><CardTitle>{order.instruction}</CardTitle><p className="mt-2 text-sm text-slate-600">{rule?.explanation ?? order.last_error ?? "Waiting for compilation."}</p></div><span className={order.enabled ? "rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-800" : "rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700"}>{order.enabled ? "Enabled" : order.compilation_status}</span></div></CardHeader><CardContent className="space-y-4">{rule ? <><p className="text-sm text-slate-600">Triggers: {rule.trigger_event_types.map((type) => type.replaceAll("_", " ")).join(", ")}</p><div className="flex flex-wrap gap-2">{rule.action_templates.map((action) => <span className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-xs" key={action.action_type}>{action.action_type.replace(/[._]/g, " ")}<RiskBadge risk={action.risk_level} /></span>)}</div>{rule.warnings.length ? <ul className="list-disc pl-5 text-sm text-amber-800">{rule.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}</> : null}<div className="flex flex-wrap gap-2"><Button disabled={busy || order.compilation_status !== "compiled"} onClick={onToggle} type="button" variant="outline">{order.enabled ? "Disable" : "Enable"}</Button><Button disabled={busy} onClick={onEdit} type="button" variant="outline">Edit</Button><Button disabled={busy || !order.enabled} onClick={onSimulate} type="button" variant="outline">Simulate</Button><Button className="text-red-700" disabled={busy} onClick={onDelete} type="button" variant="ghost">Delete</Button></div></CardContent></Card>;
}
