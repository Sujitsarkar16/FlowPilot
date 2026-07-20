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
import {
  eventMatchesSearch,
  eventTypes,
  formatDate,
  readable,
} from "@/features/events/event-utils";

type DisplayEvent = { event: EventListItem; status: string };

export function EventsList() {
  const pathname = usePathname(),
    router = useRouter(),
    params = useSearchParams();
  const cursor = params.get("cursor") ?? undefined,
    type = params.get("type") ?? undefined,
    dateFrom = params.get("date_from") ?? undefined,
    dateTo = params.get("date_to") ?? undefined,
    deleted = params.get("deleted") === "1";
  const search = params.get("search") ?? "",
    status = params.get("status") ?? "";
  const query = useMemo(
    () => ({
      cursor,
      limit: 20,
      type: type as LifeEventType | undefined,
      date_from: dateFrom,
      date_to: dateTo,
    }),
    [cursor, dateFrom, dateTo, type],
  );
  const [searchDraft, setSearchDraft] = useState(search),
    [events, setEvents] = useState<DisplayEvent[]>([]),
    [nextCursor, setNextCursor] = useState<string | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState<unknown>(null);
  useEffect(() => {
    setSearchDraft(search);
  }, [search]);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.listEvents(query);
      setEvents(
        result.items
          .map((event) => ({ event, status: event.latest_plan?.status ?? "received" }))
          .sort((a, b) => Date.parse(b.event.occurred_at) - Date.parse(a.event.occurred_at)),
      );
      setNextCursor(result.next_cursor);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  }, [query]);
  useEffect(() => {
    void load();
  }, [load]);
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params.toString());
    next.delete("deleted");
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "cursor") next.delete("cursor");
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`);
  };
  const clear = () => {
    setSearchDraft("");
    router.replace(pathname);
  };
  const filteredEvents = events.filter(
    ({ event, status: itemStatus }) =>
      (!status || itemStatus === status) && eventMatchesSearch(event, searchDraft),
  );
  return (
    <main className="mx-auto max-w-6xl p-4 pb-24 sm:p-6 md:pb-8 lg:p-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
            Activity
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            See important updates FlowPilot noticed and what happened next.
          </p>
        </div>
        <Button asChild>
          <Link href="/events/new">Tell FlowPilot what happened</Link>
        </Button>
      </header>
      {deleted ? (
        <p
          aria-live="polite"
          className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm font-medium text-emerald-800"
          role="status"
        >
          The event and its FlowPilot plan were deleted.
        </p>
      ) : null}
      <details className="mb-6 rounded-xl border border-slate-200 bg-white shadow-sm">
        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-800">
          Search and filter
        </summary>
        <form
          className="grid gap-4 border-t border-slate-100 p-4 sm:grid-cols-2 lg:grid-cols-3"
          onSubmit={(event) => {
            event.preventDefault();
            update("search", searchDraft);
          }}
        >
          <label className="text-sm font-medium text-slate-700">
            Search
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              onChange={(event) => setSearchDraft(event.target.value)}
              value={searchDraft}
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Kind
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              onChange={(event) => update("type", event.target.value)}
              value={type ?? ""}
            >
              <option value="">Everything</option>
              {eventTypes.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {readable(eventType)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium text-slate-700">
            What happened
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              onChange={(event) => update("status", event.target.value)}
              value={status}
            >
              <option value="">Any status</option>
              {[
                { value: "received", label: "Not reviewed" },
                { value: "draft", label: "Getting ready" },
                { value: "policy_checked", label: "Ready to start" },
                { value: "running", label: "In progress" },
                { value: "waiting_approval", label: "Needs your approval" },
                { value: "completed", label: "Finished" },
                { value: "failed", label: "Needs attention" },
                { value: "cancelled", label: "Cancelled" },
              ].map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium text-slate-700">
            From
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              onChange={(event) => update("date_from", event.target.value)}
              type="date"
              value={dateFrom ?? ""}
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            To
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              onChange={(event) => update("date_to", event.target.value)}
              type="date"
              value={dateTo ?? ""}
            />
          </label>
          <div className="flex items-end gap-2">
            <Button type="submit" variant="outline">
              Apply
            </Button>
            <Button onClick={clear} type="button" variant="ghost">
              Clear
            </Button>
          </div>
        </form>
      </details>
      {error ? (
        <div className="space-y-3">
          <ErrorState error={error} title="Activity could not be loaded" />
          <Button onClick={() => void load()} type="button" variant="outline">
            Try again
          </Button>
        </div>
      ) : loading ? (
        <LoadingSkeleton className="h-48" label="Loading activity" />
      ) : !filteredEvents.length ? (
        <EmptyState
          action={
            <Button asChild>
              <Link href="/events/new">Tell FlowPilot what happened</Link>
            </Button>
          }
          description="New updates from connected apps and anything you add will appear here."
          title="No activity found"
        />
      ) : (
        <section aria-label="Activity" className="space-y-4">
          {filteredEvents.map(({ event, status: itemStatus }) => (
            <Card key={event.id}>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-lg">
                      <Link className="hover:underline" href={`/dashboard/events/${event.id}`}>
                        {event.summary}
                      </Link>
                    </CardTitle>
                    <p className="mt-1 text-sm text-slate-600">
                      {formatDate(event.occurred_at)} · {readable(event.type)}
                    </p>
                  </div>
                  <StatusBadge status={itemStatus} />
                </div>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 text-sm">
                <p className="text-slate-600">
                  {event.latest_plan ? (
                    <>
                      <span className="font-medium text-slate-800">FlowPilot:</span>{" "}
                      {event.latest_plan.objective}
                    </>
                  ) : (
                    "No actions needed yet."
                  )}
                </p>
                <Link
                  className="font-medium text-indigo-700 hover:underline"
                  href={`/dashboard/events/${event.id}`}
                >
                  View details
                </Link>
              </CardContent>
            </Card>
          ))}
        </section>
      )}
      {!loading && !error && nextCursor ? (
        <div className="mt-6">
          <Button onClick={() => update("cursor", nextCursor)} type="button" variant="outline">
            Show more
          </Button>
        </div>
      ) : null}
    </main>
  );
}
