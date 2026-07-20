"use client";

import {
  CalendarDays,
  CheckCircle2,
  CloudSun,
  Download,
  FileText,
  FolderOpen,
  Mail,
  MessageCircle,
  Sparkles,
  TicketCheck,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActionDag } from "@/features/events/action-dag";
import { usePlanStream } from "@/features/events/use-plan-stream";
import {
  attachmentBase64,
  attachmentIsValid,
  attachmentMimeType,
  entityValue,
  EVENT_ATTACHMENT_ACCEPT,
  formatDate,
  MAX_EVENT_ATTACHMENTS,
  readable,
} from "@/features/events/event-utils";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type {
  EventAttachment,
  EventDetail as EventRecord,
  Plan,
  PlanAction,
  TimelineEntry,
} from "@/lib/api/types";

type Intent = {
  kind: "execute" | "cancel" | "promote" | "retry" | "rollback" | "delete";
  action?: PlanAction;
};
const executeStatuses = ["draft", "policy_checked"],
  cancelStatuses = ["draft", "policy_checked", "running", "waiting_approval"];
const CANCELLABLE_ACTION_STATUSES = new Set(["planned", "waiting_approval", "approved", "queued"]);
const ACTIVE_ACTION_STATUSES = new Set(["waiting_approval", "approved", "queued", "running"]);
const RUNNING_STATUSES = new Set(["running", "waiting_approval"]);

function timelineIcon(eventName: string) {
  const name = eventName.toLocaleLowerCase();
  if (name.includes("email") || name.includes("inbox")) return Mail;
  if (name.includes("calendar")) return CalendarDays;
  if (name.includes("ticket") || name.includes("travel")) return TicketCheck;
  if (name.includes("weather")) return CloudSun;
  if (name.includes("document") || name.includes("file") || name.includes("saved")) return FileText;
  if (name.includes("message") || name.includes("approval")) return MessageCircle;
  if (name.includes("complete") || name.includes("created")) return CheckCircle2;
  return Sparkles;
}

function timelineLabel(eventName: string) {
  const label = readable(eventName);
  return label.charAt(0).toLocaleUpperCase() + label.slice(1);
}

function timelineActor(actorType: string) {
  return actorType === "system" ? "FlowPilot" : timelineLabel(actorType);
}

function formatFileSize(bytes: number) {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MiB`
    : `${Math.ceil(bytes / 1024)} KB`;
}

function blobFromBase64(contentBase64: string, mimeType: string) {
  const binary = atob(contentBase64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new Blob([bytes], { type: mimeType });
}

export function EventDetail({
  eventId,
  workspace = false,
}: {
  eventId: string;
  workspace?: boolean;
}) {
  const router = useRouter();
  const [event, setEvent] = useState<EventRecord | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [attachments, setAttachments] = useState<EventAttachment[]>([]);
  const [downloadingAttachmentId, setDownloadingAttachmentId] = useState<string | null>(null);
  const [uploadingDocuments, setUploadingDocuments] = useState(false);
  const [folderOpen, setFolderOpen] = useState(false);
  const folderDialogRef = useRef<HTMLDialogElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reveal, setReveal] = useState(false);
  const [intent, setIntent] = useState<Intent | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextEvent, nextTimeline, nextAttachments] = await Promise.all([
        api.getEvent(eventId),
        api.getEventTimeline(eventId, { limit: 50 }),
        api.listEventAttachments(eventId),
      ]);
      setEvent(nextEvent);
      setTimeline(nextTimeline.items);
      setAttachments(nextAttachments);
      setPlan(nextEvent.latest_plan ? await api.getPlan(nextEvent.latest_plan.id) : null);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const dialog = folderDialogRef.current;
    if (!dialog) return;
    if (folderOpen && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    } else if (!folderOpen && dialog.open) {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    }
  }, [folderOpen]);

  // SSE live-update while plan is executing
  const isRunning = plan !== null && RUNNING_STATUSES.has(plan.status);
  const { plan: streamedPlan, state: streamState } = usePlanStream(isRunning ? plan?.id : null);
  useEffect(() => {
    if (streamedPlan) setPlan(streamedPlan as unknown as Plan);
  }, [streamedPlan]);

  // Polling fallback: re-fetch every 10s if SSE is not streaming
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (isRunning && streamState !== "streaming") {
      pollRef.current = setInterval(() => void load(), 10_000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isRunning, streamState, load]);

  const applyAction = (updated: PlanAction) =>
    setPlan((current) =>
      current
        ? { ...current, actions: current.actions.map((a) => (a.id === updated.id ? updated : a)) }
        : current,
    );

  const mutate = async () => {
    if (!intent || !event) return;
    setBusy(true);
    setError(null);
    try {
      if (intent.kind === "delete") {
        await api.deleteEvent(event.id);
        setIntent(null);
        router.replace("/dashboard/events?deleted=1");
        return;
      }
      if (!plan) return;
      if (intent.kind === "execute") setPlan(await api.executePlan(plan.id));
      else if (intent.kind === "cancel") setPlan(await api.cancelPlan(plan.id));
      else if (intent.kind === "promote") setPlan(await api.promotePlan(plan.id));
      else if (intent.action)
        applyAction(
          intent.kind === "retry"
            ? await api.retryAction(intent.action.id)
            : await api.rollbackAction(intent.action.id),
        );
      setIntent(null);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };
  const downloadAttachment = async (attachment: EventAttachment) => {
    if (!event) return;
    setDownloadingAttachmentId(attachment.id);
    setError(null);
    try {
      const content = await api.getEventAttachmentContent(event.id, attachment.id);
      const url = URL.createObjectURL(blobFromBase64(content.content_base64, content.mime_type));
      const link = document.createElement("a");
      link.href = url;
      link.download = content.filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught);
    } finally {
      setDownloadingAttachmentId(null);
    }
  };
  const uploadDocuments = async (files: File[]) => {
    if (!event || !files.length) return;
    const invalid = files.find((file) => !attachmentIsValid(file));
    if (invalid) {
      setError(new Error(`${invalid.name} must be a supported file no larger than 5 MiB.`));
      return;
    }
    if (attachments.length + files.length > MAX_EVENT_ATTACHMENTS) {
      setError(new Error("An event folder can contain up to 20 documents."));
      return;
    }
    setUploadingDocuments(true);
    setError(null);
    try {
      for (const file of files) {
        await api.uploadEventAttachment(event.id, {
          name: file.name,
          mime_type: attachmentMimeType(file),
          content_base64: await attachmentBase64(file),
        });
      }
      setAttachments(await api.listEventAttachments(event.id));
    } catch (caught) {
      setError(caught);
    } finally {
      setUploadingDocuments(false);
    }
  };

  if (loading)
    return (
      <main className="mx-auto max-w-6xl p-4 sm:p-6">
        <LoadingSkeleton className="h-96" label="Loading activity details" />
      </main>
    );
  if (error && !event)
    return (
      <main className="mx-auto max-w-6xl space-y-3 p-4 sm:p-6">
        <ErrorState error={error} title="This activity could not be loaded" />
        <Button onClick={() => void load()} type="button" variant="outline">
          Try again
        </Button>
      </main>
    );
  if (!event)
    return (
      <main className="mx-auto max-w-6xl p-4 sm:p-6">
        <EmptyState description="It may have been deleted." title="Activity not found" />
      </main>
    );
  const sensitiveCount = event.entities.filter((entity) => entity.is_sensitive).length,
    approvalCount = plan?.actions.filter((action) => action.requires_approval).length ?? 0,
    completedCount = plan?.actions.filter((action) => action.status === "completed").length ?? 0,
    failedCount = plan?.actions.filter((action) => action.status === "failed").length ?? 0,
    services = plan ? [...new Set(plan.actions.map((action) => action.connector))] : [],
    hasRunningAction = plan?.actions.some((action) => action.status === "running") ?? false,
    hasActiveAction =
      plan?.actions.some((action) => ACTIVE_ACTION_STATUSES.has(action.status)) ?? false,
    canCancelPlan =
      plan !== null &&
      !hasRunningAction &&
      (cancelStatuses.includes(plan.status) ||
        plan.actions.some((action) => CANCELLABLE_ACTION_STATUSES.has(action.status))),
    deleteBlocked =
      plan !== null && (["running", "waiting_approval"].includes(plan.status) || hasActiveAction),
    deleteBlockedMessage = hasRunningAction
      ? "Wait for the running step to finish before deleting this event"
      : "Cancel the active plan before deleting this event";
  const dialogTitle =
    intent?.kind === "delete"
      ? "Delete this event?"
      : intent
        ? `${readable(intent.kind)} this ${intent.action ? "step" : "plan"}?`
        : "";
  const dialogDescription =
    intent?.kind === "delete"
      ? "This permanently removes this event and its FlowPilot plan. Work already created in connected apps will stay. Security history is retained."
      : intent?.kind === "rollback"
        ? "This undoes the completed step when the connected app supports it."
        : "This changes the plan or step and may start work in a connected app.";
  const folderFiles = attachments.length ? (
    <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
      {attachments.map((attachment) => (
        <li
          className="flex flex-wrap items-center justify-between gap-3 px-3 py-3"
          key={attachment.id}
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-slate-900">{attachment.filename}</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {attachment.mime_type} · {formatFileSize(attachment.size_bytes)}
            </p>
          </div>
          <Button
            disabled={downloadingAttachmentId === attachment.id}
            onClick={() => void downloadAttachment(attachment)}
            size="sm"
            type="button"
            variant="outline"
          >
            <Download aria-hidden="true" className="mr-1 size-3.5" />
            {downloadingAttachmentId === attachment.id ? "Preparing…" : "Download"}
          </Button>
        </li>
      ))}
    </ul>
  ) : (
    <p className="text-sm text-slate-600">
      This folder is ready. Add a ticket now, or generated documents will appear after the plan
      runs.
    </p>
  );
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 pb-24 sm:p-6 md:pb-8">
      <Link
        className="text-sm font-medium text-indigo-700 hover:underline"
        href={workspace ? `/dashboard/events/${event.id}` : "/dashboard/events"}
      >
        ← {workspace ? "Event overview" : "All activity"}
      </Link>
      <header>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            {workspace ? (
              <p className="mb-1 text-sm font-medium text-indigo-700">Private event workspace</p>
            ) : null}
            <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
              {event.summary}
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              <time dateTime={event.occurred_at}>{formatDate(event.occurred_at)}</time> ·{" "}
              {readable(event.importance)} priority
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-2 text-right">
            {!workspace ? (
              <Button onClick={() => setFolderOpen(true)} type="button" variant="outline">
                <FolderOpen aria-hidden="true" className="mr-2 size-4" />
                Open event folder
              </Button>
            ) : null}
            {canCancelPlan ? (
              <Button onClick={() => setIntent({ kind: "cancel" })} type="button" variant="outline">
                Cancel plan
              </Button>
            ) : null}
            <Button
              className="border-red-200 text-red-700 hover:bg-red-50"
              disabled={deleteBlocked}
              onClick={() => setIntent({ kind: "delete" })}
              title={deleteBlocked ? deleteBlockedMessage : undefined}
              type="button"
              variant="outline"
            >
              Delete event
            </Button>
            {deleteBlocked ? (
              <p className="basis-full mt-1 max-w-52 text-xs text-slate-500">
                {deleteBlockedMessage}.
              </p>
            ) : null}
          </div>
        </div>
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-medium text-slate-700">Technical details</summary>
          <dl className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-md bg-slate-50 p-3">
              <dt className="text-slate-500">From</dt>
              <dd className="mt-1 font-medium text-slate-900">{readable(event.source)}</dd>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <dt className="text-slate-500">Kind</dt>
              <dd className="mt-1 font-medium text-slate-900">{readable(event.type)}</dd>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <dt className="text-slate-500">Interpretation confidence</dt>
              <dd className="mt-1 font-medium text-slate-900">
                {Math.round(event.confidence * 100)}%
              </dd>
            </div>
          </dl>
        </details>
      </header>
      {error ? <ErrorState error={error} title="That change could not be completed" /> : null}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>Details</CardTitle>
            <Button
              aria-pressed={reveal}
              onClick={() => setReveal((current) => !current)}
              size="sm"
              type="button"
              variant="outline"
            >
              {reveal ? "Hide protected values" : "Show protected values"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            {event.entities.length ? (
              event.entities.map((entity, index) => (
                <div className="rounded-md bg-slate-50 p-3" key={`${entity.kind}-${index}`}>
                  <dt className="font-medium text-slate-900">
                    {readable(entity.kind)}
                    {entity.is_sensitive ? " (protected)" : ""}
                  </dt>
                  <dd className="mt-1 text-slate-600">{entityValue(entity, reveal)}</dd>
                </div>
              ))
            ) : (
              <div>
                <dt className="sr-only">Details found</dt>
                <dd className="text-slate-600">No extra details were found.</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>
      {workspace ? (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <FolderOpen aria-hidden="true" className="size-5 text-indigo-600" />
                <div>
                  <CardTitle>Event folder</CardTitle>
                  <p className="mt-1 text-sm text-slate-600">
                    Details, generated checklists, tickets, and your documents stay private here
                    even when Drive is unavailable.
                  </p>
                </div>
              </div>
              <label className="inline-flex h-8 cursor-pointer items-center justify-center rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-900 hover:bg-slate-100 focus-within:ring-2 focus-within:ring-indigo-500">
                <Upload aria-hidden="true" className="mr-1 size-3.5" />
                {uploadingDocuments ? "Uploading…" : "Add documents"}
                <input
                  accept={EVENT_ATTACHMENT_ACCEPT}
                  className="sr-only"
                  disabled={uploadingDocuments}
                  multiple
                  onChange={(changeEvent) => {
                    const files = Array.from(changeEvent.target.files ?? []);
                    changeEvent.target.value = "";
                    void uploadDocuments(files);
                  }}
                  type="file"
                />
              </label>
            </div>
            <p className="text-xs text-slate-500">
              PDF, DOCX, PNG, JPEG, TXT, or Markdown; up to 5 MiB each and 20 per event.
            </p>
          </CardHeader>
          <CardContent>{folderFiles}</CardContent>
        </Card>
      ) : null}
      {plan ? (
        <>
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                    What FlowPilot plans to do
                  </p>
                  <CardTitle>{plan.objective}</CardTitle>
                  <p className="mt-2 text-sm text-slate-600">
                    <span className="font-medium text-slate-700">Why:</span>{" "}
                    {plan.planner_rationale ??
                      plan.summary ??
                      "No additional explanation was provided."}
                  </p>
                </div>
                <StatusBadge status={plan.status} />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <details className="rounded-lg bg-slate-50 p-3">
                <summary className="cursor-pointer text-sm font-medium text-slate-800">
                  Plan details
                </summary>
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                  <div>
                    <dt className="text-slate-500">Steps</dt>
                    <dd className="font-semibold text-slate-900">{plan.actions.length}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Finished</dt>
                    <dd className="font-semibold text-slate-900">
                      {completedCount} of {plan.actions.length}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Need your approval</dt>
                    <dd className="font-semibold text-slate-900">{approvalCount}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Connected apps</dt>
                    <dd className="font-semibold text-slate-900">
                      {services.map(readable).join(", ") || "None"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Need attention</dt>
                    <dd className="font-semibold text-slate-900">{failedCount}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Privacy</dt>
                    <dd className="font-semibold text-slate-900">
                      {sensitiveCount} protected value{sensitiveCount === 1 ? "" : "s"}
                    </dd>
                  </div>
                </dl>
              </details>
              <div className="flex flex-wrap gap-2">
                {executeStatuses.includes(plan.status) ? (
                  <Button onClick={() => setIntent({ kind: "execute" })} type="button">
                    Start plan
                  </Button>
                ) : null}
                {plan.status === "waiting_approval" ? (
                  <Button asChild>
                    <Link href="/dashboard/approvals">Review and approve</Link>
                  </Button>
                ) : null}
                {canCancelPlan ? (
                  <Button
                    onClick={() => setIntent({ kind: "cancel" })}
                    type="button"
                    variant="outline"
                  >
                    Cancel plan
                  </Button>
                ) : null}
                {plan.is_shadow ? (
                  <Button
                    onClick={() => setIntent({ kind: "promote" })}
                    type="button"
                    variant="outline"
                  >
                    Use this plan
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>
          {plan.is_shadow ? (
            <Card>
              <CardHeader>
                <CardTitle>Preview</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-slate-600">
                {plan.summary ?? plan.objective}
              </CardContent>
            </Card>
          ) : null}
          <ActionDag actions={plan.actions} />
          <section aria-label="Step options" className="flex flex-wrap gap-2">
            {plan.actions
              .filter(
                (action) =>
                  action.status === "failed" ||
                  (action.status === "completed" && action.rollback_supported),
              )
              .map((action) => (
                <div className="flex items-center gap-2" key={action.id}>
                  <span className="text-sm text-slate-600">{readable(action.action_type)}</span>
                  {action.status === "failed" ? (
                    <Button
                      onClick={() => setIntent({ kind: "retry", action })}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      Try again
                    </Button>
                  ) : null}
                  {action.status === "completed" && action.rollback_supported ? (
                    <Button
                      onClick={() => setIntent({ kind: "rollback", action })}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      Undo
                    </Button>
                  ) : null}
                </div>
              ))}
          </section>
        </>
      ) : (
        <EmptyState
          description="FlowPilot did not find any follow-up work for this update."
          title="Nothing to do yet"
        />
      )}
      <Card className="overflow-hidden">
        <CardHeader className="border-b border-slate-100 bg-gradient-to-r from-indigo-50/70 to-white pb-5">
          <div className="flex items-start gap-3">
            <span
              aria-hidden="true"
              className="grid size-10 shrink-0 place-items-center rounded-xl bg-indigo-600 text-white shadow-sm"
            >
              <Sparkles className="size-5" strokeWidth={2.25} />
            </span>
            <div>
              <CardTitle className="text-lg text-slate-950" id="timeline-title">
                Activity timeline
              </CardTitle>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                Every update FlowPilot made for this event, in order.
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-5 sm:p-6">
          {timeline.length ? (
            <ol aria-labelledby="timeline-title">
              {timeline.map((entry, index) => {
                const Icon = timelineIcon(entry.event_name);
                const isLast = index === timeline.length - 1;
                return (
                  <li
                    className="grid grid-cols-[3.5rem_2rem_minmax(0,1fr)] gap-x-3 sm:grid-cols-[5rem_2.5rem_minmax(0,1fr)] sm:gap-x-4"
                    key={entry.id}
                  >
                    <time
                      className="pt-2 text-right text-xs font-medium tabular-nums text-slate-500"
                      dateTime={entry.created_at}
                      title={formatDate(entry.created_at)}
                    >
                      {new Date(entry.created_at).toLocaleTimeString(undefined, {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </time>
                    <div className="relative flex justify-center">
                      {!isLast ? (
                        <span
                          aria-hidden="true"
                          className="absolute top-9 h-[calc(100%-1.15rem)] w-px bg-slate-200"
                        />
                      ) : null}
                      <span className="relative z-10 mt-1 grid size-8 place-items-center rounded-full border-4 border-white bg-indigo-100 text-indigo-700 shadow-sm">
                        <Icon aria-hidden="true" className="size-3.5" strokeWidth={2.5} />
                      </span>
                    </div>
                    <div className={isLast ? "pb-0" : "pb-5"}>
                      <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm transition-colors hover:border-indigo-200 hover:bg-indigo-50/30">
                        <p className="font-medium text-slate-900">
                          {timelineLabel(entry.event_name)}
                        </p>
                        <p className="mt-1 text-sm text-slate-600">
                          <span className="font-medium text-slate-700">
                            {timelineActor(entry.actor_type)}
                          </span>
                          <span aria-hidden="true" className="mx-1.5 text-slate-300">
                            ·
                          </span>
                          <time dateTime={entry.created_at}>{formatDate(entry.created_at)}</time>
                        </p>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
              <p className="font-medium text-slate-800">No activity yet</p>
              <p className="mt-1 text-sm text-slate-600">
                New updates will appear here as FlowPilot works on this event.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
      <dialog
        aria-labelledby="event-folder-dialog-title"
        className="m-auto w-[min(100%-2rem,48rem)] rounded-xl border border-slate-200 bg-white p-0 text-slate-950 shadow-2xl backdrop:bg-slate-950/50"
        onCancel={() => setFolderOpen(false)}
        onClick={(clickEvent) => {
          if (clickEvent.target === clickEvent.currentTarget) setFolderOpen(false);
        }}
        ref={folderDialogRef}
      >
        <div className="max-h-[calc(100vh-2rem)] overflow-y-auto p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-2">
              <FolderOpen aria-hidden="true" className="size-5 shrink-0 text-indigo-600" />
              <div className="min-w-0">
                <h2 className="truncate text-xl font-semibold" id="event-folder-dialog-title">
                  {event.summary}
                </h2>
                <p className="mt-1 text-sm text-slate-600">Private event folder</p>
              </div>
            </div>
            <Button
              aria-label="Close event folder"
              onClick={() => setFolderOpen(false)}
              size="sm"
              type="button"
              variant="ghost"
            >
              <X aria-hidden="true" className="size-4" />
            </Button>
          </div>

          <section aria-labelledby="event-folder-details-title" className="mt-6">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-semibold text-slate-900" id="event-folder-details-title">
                Event details
              </h3>
              <Button
                aria-pressed={reveal}
                onClick={() => setReveal((current) => !current)}
                size="sm"
                type="button"
                variant="outline"
              >
                {reveal ? "Hide protected values" : "Show protected values"}
              </Button>
            </div>
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
              {event.entities.length ? (
                event.entities.map((entity, index) => (
                  <div className="rounded-md bg-slate-50 p-3" key={`${entity.kind}-${index}`}>
                    <dt className="font-medium text-slate-900">
                      {readable(entity.kind)}
                      {entity.is_sensitive ? " (protected)" : ""}
                    </dt>
                    <dd className="mt-1 text-slate-600">{entityValue(entity, reveal)}</dd>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-600">No extra details were found.</p>
              )}
            </dl>
          </section>

          <section aria-labelledby="event-folder-files-title" className="mt-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-slate-900" id="event-folder-files-title">
                  Files
                </h3>
                <p className="mt-1 text-sm text-slate-600">
                  Tickets and generated documents are kept here even when Drive is unavailable.
                </p>
              </div>
              <label className="inline-flex h-8 cursor-pointer items-center justify-center rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-900 hover:bg-slate-100 focus-within:ring-2 focus-within:ring-indigo-500">
                <Upload aria-hidden="true" className="mr-1 size-3.5" />
                {uploadingDocuments ? "Uploading…" : "Add files"}
                <input
                  accept={EVENT_ATTACHMENT_ACCEPT}
                  className="sr-only"
                  disabled={uploadingDocuments}
                  multiple
                  onChange={(changeEvent) => {
                    const files = Array.from(changeEvent.target.files ?? []);
                    changeEvent.target.value = "";
                    void uploadDocuments(files);
                  }}
                  type="file"
                />
              </label>
            </div>
            <div className="mt-3">{folderFiles}</div>
          </section>

          <div className="mt-6 flex justify-end gap-3 border-t border-slate-200 pt-4">
            <Button onClick={() => setFolderOpen(false)} type="button" variant="outline">
              Close
            </Button>
            <Button asChild>
              <Link
                href={`/dashboard/events/${event.id}/workspace`}
                onClick={() => setFolderOpen(false)}
              >
                Open full workspace
              </Link>
            </Button>
          </div>
        </div>
      </dialog>
      <ConfirmDialog
        busy={busy}
        confirmLabel={
          intent?.kind === "delete"
            ? "Delete event"
            : intent?.kind === "execute"
              ? "Start plan"
              : intent
                ? readable(intent.kind)
                : "Confirm"
        }
        description={dialogDescription}
        destructive={
          intent?.kind === "cancel" || intent?.kind === "rollback" || intent?.kind === "delete"
        }
        onCancel={() => setIntent(null)}
        onConfirm={() => void mutate()}
        open={intent !== null}
        title={dialogTitle}
      />
    </main>
  );
}
