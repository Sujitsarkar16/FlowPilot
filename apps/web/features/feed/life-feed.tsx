"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { DashboardSummary, EventListItem, EventPlanSummary } from "@/lib/api/types";
import { formatDate, readable } from "@/features/events/event-utils";

type FeedItem = { event: EventListItem; status: string; plan: EventPlanSummary | null };

export function LifeFeed() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [dashboard, events] = await Promise.all([api.getDashboardSummary(), api.listEvents({ limit: 10 })]);
      setSummary(dashboard);
      setItems(events.items.map((event) => ({ event, status: event.latest_plan?.status ?? "received", plan: event.latest_plan })).sort((a, b) => Date.parse(b.event.occurred_at) - Date.parse(a.event.occurred_at)));
    } catch (caught) { setError(caught); } finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  if (loading) return <main className="mx-auto max-w-6xl p-4 sm:p-6 lg:p-8"><LoadingSkeleton className="h-72" label="Loading your Life Feed" /></main>;
  if (error) return <main className="mx-auto max-w-6xl space-y-3 p-4 sm:p-6 lg:p-8"><ErrorState error={error} title="Life Feed could not be loaded" /><Button onClick={() => void load()} type="button" variant="outline">Try again</Button></main>;
  return <main className="mx-auto max-w-6xl p-4 pb-24 sm:p-6 md:pb-8 lg:p-8"><header className="mb-8"><h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Life Feed</h1><p className="mt-2 text-sm leading-6 text-slate-600">A chronological view of important events and the actions FlowPilot is handling.</p></header>
    <section aria-label="Today’s summary" className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[["Events today", summary?.events_today], ["Completed", summary?.actions_completed], ["Awaiting approval", summary?.pending_approvals], ["Failed", summary?.failed_actions], ["Minutes saved", summary?.time_saved_minutes]].map(([label, value]) => <Card key={String(label)}><CardContent className="p-4"><p className="text-sm text-slate-600">{label}</p><p className="mt-1 text-2xl font-semibold text-slate-950">{value ?? 0}</p></CardContent></Card>)}</section>
    {!items.length ? <EmptyState action={<Button asChild><Link href="/events/new">Add a manual event</Link></Button>} description="Add an event or connect a source to start building a chronological feed." title="Your Life Feed is ready" /> : <section aria-label="Recent activity" className="space-y-4">{items.map(({ event, status, plan }) => <Card key={event.id}><CardHeader><div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle className="text-lg"><Link className="hover:underline" href={`/dashboard/events/${event.id}`}>{event.summary}</Link></CardTitle><p className="mt-1 text-sm text-slate-600">{formatDate(event.occurred_at)} · {readable(event.type)}</p></div><StatusBadge status={status} /></div></CardHeader><CardContent className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600"><span>{plan ? "Latest plan sub-actions:" : "Waiting for a plan to be generated."}</span><div className="flex flex-wrap gap-2">{plan?.completed_actions ? <span className="rounded-full bg-emerald-50 px-2 py-1 text-emerald-800">{plan.completed_actions} completed</span> : null}{plan?.pending_actions ? <span className="rounded-full bg-amber-50 px-2 py-1 text-amber-800">{plan.pending_actions} pending</span> : null}{plan?.failed_actions ? <span className="rounded-full bg-red-50 px-2 py-1 text-red-800">{plan.failed_actions} failed</span> : null}</div><div className="flex gap-3"><Link className="font-medium text-indigo-700 hover:underline" href={`/dashboard/events/${event.id}`}>View event</Link>{status === "waiting_approval" ? <Link className="font-medium text-indigo-700 hover:underline" href="/dashboard/approvals">Review approval</Link> : null}</div></CardContent></Card>)}</section>}</main>;
}
