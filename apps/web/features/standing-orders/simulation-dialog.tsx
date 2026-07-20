"use client";

import { type FormEvent, useState } from "react";

import { ErrorState } from "@/components/error-state";
import { RiskBadge } from "@/components/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { StandingOrderSimulation } from "@/lib/api/types";

// Pre-defined sample events per trigger type so the user isn't staring at a blank box.
const SAMPLE_EVENTS: Record<string, string> = {
  travel_booked:
    "I just received a booking confirmation email for my flight from Bangalore to Dubai on 25 Aug, PNR: XYZ123, operated by IndiGo.",
  travel_changed:
    "My flight BLR→DXB on 25 Aug has been rescheduled to 26 Aug at 10:00. Please update my plans.",
  client_opportunity:
    "New lead from Acme Corp — they want a quote for a 3-month contract starting September.",
  client_confirmed:
    "Acme Corp signed the contract today. Kickoff meeting scheduled for Monday 9 AM.",
  salary_credited: "Salary of ₹1,50,000 credited to my account on 1 July by my employer.",
  subscription_renewal:
    "Your Netflix subscription of ₹649 will renew on 20 July. Confirm to continue.",
  generic_important_event:
    "My passport expires in 90 days. I need to renew it before my upcoming travel.",
};

const TRIGGER_LABELS: Record<string, string> = {
  travel_booked: "✈️ Flight / Hotel booked",
  travel_changed: "🔄 Travel plan changed",
  client_opportunity: "🤝 New client lead",
  client_confirmed: "✅ Client confirmed",
  salary_credited: "💰 Salary credited",
  subscription_renewal: "🔔 Subscription renewal",
  generic_important_event: "📌 Any important event",
};

export function SimulationDialog({
  busy,
  error,
  onClose,
  onSubmit,
  open,
  result,
  defaultTrigger,
}: {
  busy: boolean;
  error: unknown;
  onClose: () => void;
  onSubmit: (sampleEvent: string) => Promise<void>;
  open: boolean;
  result: StandingOrderSimulation | null;
  defaultTrigger?: string;
}) {
  const preset = defaultTrigger ? (SAMPLE_EVENTS[defaultTrigger] ?? "") : "";
  const [sampleEvent, setSampleEvent] = useState(preset);

  if (!open) return null;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (sampleEvent.trim()) void onSubmit(sampleEvent.trim());
  };

  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 p-4"
      role="dialog"
      aria-labelledby="simulation-dialog-title"
    >
      <Card className="mx-auto mt-12 w-full max-w-2xl shadow-xl">
        <CardHeader>
          <CardTitle id="simulation-dialog-title">Test this automation</CardTitle>
          <p className="text-sm text-slate-600">
            Describe a sample event. FlowPilot will classify it and show the actions it{" "}
            <em>would</em> take — nothing is executed.
          </p>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Quick-fill presets */}
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
              Load a sample
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(SAMPLE_EVENTS).map(([key, value]) => (
                <button
                  className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800"
                  key={key}
                  onClick={() => setSampleEvent(value)}
                  type="button"
                >
                  {TRIGGER_LABELS[key] ?? key}
                </button>
              ))}
            </div>
          </div>

          <form className="space-y-3" onSubmit={submit}>
            <label className="block text-sm font-medium text-slate-900" htmlFor="simulation-event">
              Sample event description
            </label>
            <textarea
              className="min-h-32 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500"
              disabled={busy}
              id="simulation-event"
              onChange={(e) => setSampleEvent(e.target.value)}
              placeholder="Describe what happened, e.g. 'I booked a flight to Dubai for next Friday…'"
              required
              value={sampleEvent}
            />
            <div className="flex justify-end gap-2">
              <Button disabled={busy} onClick={onClose} type="button" variant="outline">
                Close
              </Button>
              <Button disabled={busy || !sampleEvent.trim()} type="submit">
                {busy ? "Simulating…" : "Run simulation"}
              </Button>
            </div>
          </form>

          {error ? <ErrorState error={error} title="Simulation failed" /> : null}
          {result ? <SimulationResult result={result} /> : null}
        </CardContent>
      </Card>
    </div>
  );
}

function SimulationResult({ result }: { result: StandingOrderSimulation }) {
  return (
    <section aria-live="polite" className="space-y-4 rounded-lg border border-slate-200 p-4">
      {/* Match verdict */}
      <div
        className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
          result.matched ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-700"
        }`}
      >
        <span aria-hidden="true">{result.matched ? "✅" : "⬜"}</span>
        {result.matched ? "This rule matches the sample." : "This rule does not match the sample."}
      </div>

      <p className="text-sm text-slate-600">
        Classified as{" "}
        <span className="font-medium text-slate-800">{result.event_type.replaceAll("_", " ")}</span>
        .
      </p>

      {/* Proposed actions */}
      {result.proposed_actions.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Actions FlowPilot would take
          </p>
          <ul className="space-y-2">
            {result.proposed_actions.map((action) => (
              <li
                className="flex items-center justify-between gap-3 rounded-md border border-slate-200 px-3 py-2 text-sm"
                key={action.action_type}
              >
                <span className="text-slate-800">{action.action_type.replace(/[._]/g, " ")}</span>
                <RiskBadge risk={action.risk_level} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <ul className="list-disc pl-5 text-sm text-amber-800">
          {result.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
