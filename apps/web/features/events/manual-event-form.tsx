"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { LifeEventType } from "@/lib/api/types";

const EXAMPLES = [
  "Your flight AA123 to Tokyo is confirmed, departing Friday at 9:00 AM.",
  "A new client wants a marketing website built by the end of next month.",
  "Your salary of 5,000 USD has been credited to your account.",
] as const;

const HINTS: { value: string; label: string }[] = [
  { value: "", label: "Let FlowPilot decide" },
  { value: "travel", label: "Travel" },
  { value: "client", label: "Client opportunity" },
  { value: "salary", label: "Salary / finance" },
];

type Phase = "idle" | "classifying" | "done";

export function ManualEventForm() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [hint, setHint] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<unknown>(null);
  const [classified, setClassified] = useState<LifeEventType | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!text.trim()) {
      setError(new Error("Describe the event before submitting."));
      return;
    }
    setPhase("classifying");
    setError(null);
    setClassified(null);
    try {
      const result = await api.createManualEvent(
        { text: text.trim(), category_hint: hint || null },
        { timeoutMs: 60_000 }, // AI classification + entity extraction can take ~20–30 s
      );
      setClassified(result.type);
      setPhase("done");
      router.push(`/dashboard/events/${result.id}`);
    } catch (caught) {
      setError(caught);
      setPhase("idle");
    }
  };

  const busy = phase === "classifying";

  return (
    <div className="mx-auto max-w-2xl p-4 pb-24 sm:p-6 md:pb-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
          Add an event
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Paste an email or describe what happened. FlowPilot interprets it and prepares a plan you
          can review.
        </p>
      </div>

      {error ? <ErrorState className="mb-4" error={error} title="Could not submit event" /> : null}

      <Card>
        <CardHeader>
          <CardTitle>Event details</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={submit}>
            <div>
              <label className="text-sm font-medium text-slate-900" htmlFor="event-text">
                What happened?
              </label>
              <textarea
                aria-describedby="event-text-help"
                className="mt-1 block min-h-40 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                disabled={busy}
                id="event-text"
                onChange={(changeEvent) => setText(changeEvent.target.value)}
                placeholder="Paste a flight confirmation, client email, or a short note…"
                required
                value={text}
              />
              <p className="mt-1 text-xs text-slate-500" id="event-text-help">
                External content is treated as data and is never executed as instructions.
              </p>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-900" htmlFor="event-hint">
                Category hint (optional)
              </label>
              <select
                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                disabled={busy}
                id="event-hint"
                onChange={(changeEvent) => setHint(changeEvent.target.value)}
                value={hint}
              >
                {HINTS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <fieldset className="rounded-md border border-slate-200 p-3">
              <legend className="px-1 text-xs font-medium text-slate-500">Try an example</legend>
              <div className="flex flex-col gap-2">
                {EXAMPLES.map((example) => (
                  <button
                    className="rounded-md border border-slate-200 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                    disabled={busy}
                    key={example}
                    onClick={() => setText(example)}
                    type="button"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </fieldset>

            {phase === "classifying" ? (
              <p aria-live="polite" className="text-sm text-slate-600" role="status">
                Interpreting your event…
              </p>
            ) : null}
            {phase === "done" && classified ? (
              <p aria-live="polite" className="text-sm font-medium text-emerald-800" role="status">
                Classified as {classified.replace(/_/g, " ")}. Opening the event…
              </p>
            ) : null}

            <div className="flex justify-end">
              <Button disabled={busy} type="submit">
                {busy ? "Interpreting…" : "Interpret event"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
