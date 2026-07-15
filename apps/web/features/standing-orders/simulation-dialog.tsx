"use client";

import { type FormEvent, useState } from "react";

import { ErrorState } from "@/components/error-state";
import { RiskBadge } from "@/components/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { StandingOrderSimulation } from "@/lib/api/types";

export function SimulationDialog({
  busy,
  error,
  onClose,
  onSubmit,
  open,
  result,
}: {
  busy: boolean;
  error: unknown;
  onClose: () => void;
  onSubmit: (sampleEvent: string) => Promise<void>;
  open: boolean;
  result: StandingOrderSimulation | null;
}) {
  const [sampleEvent, setSampleEvent] = useState("");
  if (!open) return null;
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (sampleEvent.trim()) void onSubmit(sampleEvent.trim());
  };
  return (
    <div aria-modal="true" className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/50 p-4" role="dialog">
      <Card className="mx-auto mt-12 w-full max-w-xl">
        <CardHeader><CardTitle>Simulate this rule</CardTitle><p className="text-sm text-slate-600">This only classifies a sample and proposes actions. Nothing is executed.</p></CardHeader>
        <CardContent className="space-y-4">
          <form className="space-y-3" onSubmit={submit}>
            <label className="block text-sm font-medium text-slate-900" htmlFor="simulation-event">Sample event</label>
            <textarea className="min-h-32 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" disabled={busy} id="simulation-event" onChange={(event) => setSampleEvent(event.target.value)} required value={sampleEvent} />
            <div className="flex justify-end gap-2"><Button disabled={busy} onClick={onClose} type="button" variant="outline">Close</Button><Button disabled={busy} type="submit">{busy ? "Simulating…" : "Simulate"}</Button></div>
          </form>
          {error ? <ErrorState error={error} title="Could not simulate rule" /> : null}
          {result ? <SimulationResult result={result} /> : null}
        </CardContent>
      </Card>
    </div>
  );
}

function SimulationResult({ result }: { result: StandingOrderSimulation }) {
  return <section aria-live="polite" className="space-y-3 rounded-md border border-slate-200 p-3"><p className="font-medium text-slate-950">{result.matched ? "This rule matches the sample event." : "This rule does not match the sample event."}</p><p className="text-sm text-slate-600">Classified as {result.event_type.replaceAll("_", " ")}.</p>{result.proposed_actions.map((action) => <div className="flex items-center justify-between gap-3 text-sm" key={action.action_type}><span>{action.action_type.replace(/[._]/g, " ")}</span><RiskBadge risk={action.risk_level} /></div>)}{result.warnings.length ? <ul className="list-disc pl-5 text-sm text-amber-800">{result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}</section>;
}
