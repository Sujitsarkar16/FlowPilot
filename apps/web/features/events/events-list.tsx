"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { EventListItem, LifeEventType } from "@/lib/api/types";
import { entityValue, eventMatchesSearch, eventTypes, formatDate, readable } from "@/features/events/event-utils";

type DisplayEvent = { event: EventListItem; status: string };

export function EventsList() {
  const pathname = usePathname(), router = useRouter(), params = useSearchParams();
  const cursor = params.get("cursor") ?? undefined, type = params.get("type") ?? undefined, dateFrom = params.get("date_from") ?? undefined, dateTo = params.get("date_to") ?? undefined;
  const search = params.get("search") ?? "", status = params.get("status") ?? "";
  const query = useMemo(() => ({ cursor, limit: 20, type: type as LifeEventType | undefined, date_from: dateFrom, date_to: dateTo }), [cursor, dateFrom, dateTo, type]);
  const [searchDraft, setSearchDraft] = useState(search), [events, setEvents] = useState<DisplayEvent[]>([]), [nextCursor, setNextCursor] = useState<string | null>(null), [loading, setLoading] = useState(true), [error, setError] = useState<unknown>(null);
  useEffect(() => { setSearchDraft(search); }, [search]);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { const result = await api.listEvents(query); setEvents(result.items.map((event) => ({ event, status: event.latest_plan?.status ?? "received" })).sort((a, b) => Date.parse(b.event.occurred_at) - Date.parse(a.event.occurred_at))); setNextCursor(result.next_cursor); }
    catch (caught) { setError(caught); } finally { setLoading(false); }
  }, [query]);
  useEffect(() => { void load(); }, [load]);
  const update = (key: string, value: string) => { const next = new URLSearchParams(params.toString()); if (value) next.set(key, value); else next.delete(key); if (key !== "cursor") next.delete("cursor"); router.replace(`${pathname}${next.size ? `?${next}` : ""}`); };
  const clear = () => { setSearchDraft(""); router.replace(pathname); };
  const filteredEvents = events.filter(({ event, status: itemStatus }) => (!status || itemStatus === status) && eventMatchesSearch(event, searchDraft));
  return <main className="mx-auto max-w-6xl p-4 pb-24 sm:p-6 md:pb-8 lg:p-8"><header className="mb-8 flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Events</h1><p className="mt-2 text-sm leading-6 text-slate-600">Review interpreted events without exposing sensitive entity values.</p></div><Button asChild><Link href="/events/new">Add manual event</Link></Button></header>
    <form className="mb-6 grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-3" onSubmit={(event) => { event.preventDefault(); update("search", searchDraft); }}><label className="text-sm font-medium text-slate-700">Search<input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" onChange={(event) => setSearchDraft(event.target.value)} value={searchDraft} /></label><label className="text-sm font-medium text-slate-700">Type<select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" onChange={(event) => update("type", event.target.value)} value={type ?? ""}><option value="">All types</option>{eventTypes.map((eventType) => <option key={eventType} value={eventType}>{readable(eventType)}</option>)}</select></label><label className="text-sm font-medium text-slate-700">Plan status<select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" onChange={(event) => update("status", event.target.value)} value={status}><option value="">All statuses</option>{["received", "draft", "policy_checked", "running", "waiting_approval", "completed", "failed", "cancelled"].map((value) => <option key={value} value={value}>{readable(value)}</option>)}</select></label><label className="text-sm font-medium text-slate-700">From<input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" onChange={(event) => update("date_from", event.target.value)} type="date" value={dateFrom ?? ""} /></label><label className="text-sm font-medium text-slate-700">To<input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" onChange={(event) => update("date_to", event.target.value)} type="date" value={dateTo ?? ""} /></label><div className="flex items-end gap-2"><Button type="submit" variant="outline">Apply search</Button><Button onClick={clear} type="button" variant="ghost">Clear</Button></div></form>
    {error ? <div className="space-y-3"><ErrorState error={error} title="Events could not be loaded" /><Button onClick={() => void load()} type="button" variant="outline">Try again</Button></div> : loading ? <LoadingSkeleton className="h-48" label="Loading events" /> : !filteredEvents.length ? <EmptyState action={<Button asChild><Link href="/events/new">Add a manual event</Link></Button>} description="No events match these filters yet. Connected and manual events will appear here." title="No events found" /> : <section aria-label="Events" className="space-y-4">{filteredEvents.map(({ event, status: itemStatus }) => <Card key={event.id}><CardHeader><div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle className="text-lg"><Link className="hover:underline" href={`/dashboard/events/${event.id}`}>{event.summary}</Link></CardTitle><p className="mt-1 text-sm text-slate-600">{readable(event.type)} · {formatDate(event.occurred_at)} · {Math.round(event.confidence * 100)}% confidence</p></div><StatusBadge status={itemStatus} /></div></CardHeader><CardContent><dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm"><div><dt className="font-medium text-slate-900">Importance</dt><dd className="text-slate-600">{event.importance}</dd></div>{event.entities.map((entity) => <div key={entity.kind}><dt className="font-medium text-slate-900">{readable(entity.kind)}</dt><dd className="text-slate-600">{entityValue(entity)}</dd></div>)}</dl></CardContent></Card>)}</section>}
    {!loading && !error && nextCursor ? <div className="mt-6"><Button onClick={() => update("cursor", nextCursor)} type="button" variant="outline">Load next page</Button></div> : null}</main>;
}
