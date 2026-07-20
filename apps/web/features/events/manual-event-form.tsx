"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { DictationButton } from "@/components/dictation-button";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  attachmentBase64,
  attachmentIsValid,
  attachmentMimeType,
  EVENT_ATTACHMENT_ACCEPT,
  MAX_EVENT_ATTACHMENTS,
} from "@/features/events/event-utils";
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
  const [attachments, setAttachments] = useState<File[]>([]);
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
        {
          text: text.trim(),
          category_hint: hint || null,
          ...(attachments.length
            ? {
                attachments: attachments.map((file) => ({
                  name: file.name,
                  mime_type: attachmentMimeType(file),
                  size_bytes: file.size,
                })),
              }
            : {}),
        },
        { timeoutMs: 60_000 }, // AI classification + entity extraction can take ~20–30 s
      );
      for (const file of attachments) {
        await api.uploadEventAttachment(
          result.id,
          {
            name: file.name,
            mime_type: attachmentMimeType(file),
            content_base64: await attachmentBase64(file),
          },
          { timeoutMs: 60_000 },
        );
      }
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
          Tell FlowPilot what happened
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Paste an email or describe an update. FlowPilot will work out whether anything needs to be
          done and let you review it first.
        </p>
      </div>

      {error ? (
        <ErrorState className="mb-4" error={error} title="Could not add this update" />
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>What happened?</CardTitle>
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
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <DictationButton
                  disabled={busy}
                  label="event details"
                  onError={setError}
                  onTranscript={(transcript) =>
                    setText((current) => `${current}${current.trim() ? " " : ""}${transcript}`)
                  }
                />
                <p className="text-xs text-slate-500" id="event-text-help">
                  Dictate, then review and edit the text before continuing. FlowPilot reads this as
                  information only and never follows instructions inside it.
                </p>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-900" htmlFor="event-hint">
                Help FlowPilot choose a category (optional)
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

            <div>
              <label
                className="block text-sm font-medium text-slate-900"
                htmlFor="event-attachments"
              >
                Attach tickets or documents (optional)
              </label>
              <p className="mt-0.5 text-xs text-slate-500">
                PDF, DOCX, PNG, JPEG, TXT, or Markdown; up to 5 MiB per file. Attachments stay
                private to this event.
              </p>
              <input
                accept={EVENT_ATTACHMENT_ACCEPT}
                className="mt-2 block w-full text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
                disabled={busy}
                id="event-attachments"
                multiple
                onChange={(changeEvent) => {
                  const files = Array.from(changeEvent.target.files ?? []);
                  changeEvent.target.value = "";
                  const invalid = files.find((file) => !attachmentIsValid(file));
                  if (invalid) {
                    setError(
                      new Error(`${invalid.name} must be a supported file no larger than 5 MiB.`),
                    );
                    return;
                  }
                  if (attachments.length + files.length > MAX_EVENT_ATTACHMENTS) {
                    setError(new Error("You can attach up to 20 files to one event."));
                    return;
                  }
                  setAttachments((current) => [
                    ...current,
                    ...files.filter(
                      (file) =>
                        !current.some(
                          (existing) =>
                            existing.name === file.name &&
                            existing.size === file.size &&
                            existing.lastModified === file.lastModified,
                        ),
                    ),
                  ]);
                  setError(null);
                }}
                type="file"
              />
              {attachments.length ? (
                <ul
                  className="mt-3 divide-y rounded-md border border-slate-200"
                  aria-label="Selected attachments"
                >
                  {attachments.map((file) => (
                    <li
                      className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
                      key={`${file.name}-${file.lastModified}`}
                    >
                      <span className="min-w-0 truncate text-slate-700">
                        {file.name}{" "}
                        <span className="text-slate-500">({Math.ceil(file.size / 1024)} KB)</span>
                      </span>
                      <button
                        className="shrink-0 font-medium text-indigo-700 hover:underline"
                        disabled={busy}
                        onClick={() =>
                          setAttachments((current) => current.filter((item) => item !== file))
                        }
                        type="button"
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
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
                Understanding your update…
              </p>
            ) : null}
            {phase === "done" && classified ? (
              <p aria-live="polite" className="text-sm font-medium text-emerald-800" role="status">
                Ready. Opening the details…
              </p>
            ) : null}

            <div className="flex justify-end">
              <Button disabled={busy} type="submit">
                {busy ? "Working…" : "Continue"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
