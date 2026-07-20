"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BellRing,
  CheckCircle2,
  CircleAlert,
  Clock3,
  ListTodo,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, readable } from "@/features/events/event-utils";
import { api } from "@/lib/api/client";
import type { DashboardSummary, EventListItem, EventPlanSummary } from "@/lib/api/types";

type FeedItem = { event: EventListItem; status: string; plan: EventPlanSummary | null };
type StatKey = keyof Pick<
  DashboardSummary,
  | "pending_approvals"
  | "failed_actions"
  | "actions_completed"
  | "events_today"
  | "time_saved_minutes"
>;

const STAT_CARDS: Array<{
  key: StatKey;
  label: string;
  description: string;
  icon: typeof BellRing;
  iconClassName: string;
}> = [
  {
    key: "pending_approvals",
    label: "Ready for review",
    description: "Your decision is needed",
    icon: BellRing,
    iconClassName: "bg-amber-100 text-amber-700",
  },
  {
    key: "failed_actions",
    label: "Needs attention",
    description: "Items to resolve",
    icon: CircleAlert,
    iconClassName: "bg-rose-100 text-rose-700",
  },
  {
    key: "actions_completed",
    label: "Completed",
    description: "Handled for you",
    icon: CheckCircle2,
    iconClassName: "bg-emerald-100 text-emerald-700",
  },
  {
    key: "events_today",
    label: "Signals today",
    description: "New updates noticed",
    icon: ListTodo,
    iconClassName: "bg-sky-100 text-sky-700",
  },
  {
    key: "time_saved_minutes",
    label: "Time returned",
    description: "Minutes saved today",
    icon: Clock3,
    iconClassName: "bg-violet-100 text-violet-700",
  },
];

function StatCard({
  item,
  value,
}: {
  item: (typeof STAT_CARDS)[number];
  value: number | undefined;
}) {
  const Icon = item.icon;
  return (
    <Card className="border-slate-200/80 bg-white/90 shadow-sm transition-shadow hover:shadow-md">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-slate-700">{item.label}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
              {value ?? 0}
            </p>
          </div>
          <span className={`rounded-xl p-2.5 ${item.iconClassName}`}>
            <Icon aria-hidden="true" size={18} />
          </span>
        </div>
        <p className="mt-2 text-xs text-slate-500">{item.description}</p>
      </CardContent>
    </Card>
  );
}

function FeedCard({ event, status, plan }: FeedItem) {
  return (
    <Card className="group border-slate-200/80 transition-shadow hover:shadow-md">
      <CardHeader className="gap-3 p-5 pb-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            {readable(event.type)}
          </p>
          <CardTitle className="text-lg leading-6 text-slate-950">
            <Link
              className="rounded-sm outline-none transition-colors hover:text-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500"
              href={`/dashboard/events/${event.id}`}
            >
              {event.summary}
            </Link>
          </CardTitle>
          <p className="mt-2 text-sm text-slate-600">{formatDate(event.occurred_at)}</p>
        </div>
        <StatusBadge className="shrink-0" status={status} />
      </CardHeader>
      <CardContent className="space-y-4 p-5 pt-2">
        <p className="text-sm leading-6 text-slate-600">
          {plan ? (
            <>
              <span className="font-medium text-slate-800">In progress: </span>
              {plan.objective}
            </>
          ) : (
            "No action is needed for this update."
          )}
        </p>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <div className="flex flex-wrap gap-2 text-xs font-medium">
            {plan?.completed_actions ? (
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-800">
                {plan.completed_actions} done
              </span>
            ) : null}
            {plan?.pending_actions ? (
              <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-800">
                {plan.pending_actions} waiting
              </span>
            ) : null}
            {plan?.failed_actions ? (
              <span className="rounded-full bg-rose-50 px-2.5 py-1 text-rose-800">
                {plan.failed_actions} need attention
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-4 text-sm font-medium">
            <Link
              className="inline-flex items-center gap-1 text-indigo-700 hover:text-indigo-900 hover:underline"
              href={`/dashboard/events/${event.id}`}
            >
              Details <ArrowRight aria-hidden="true" size={15} />
            </Link>
            {status === "waiting_approval" ? (
              <Link
                className="text-indigo-700 hover:text-indigo-900 hover:underline"
                href="/dashboard/approvals"
              >
                Review now
              </Link>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ControlCard() {
  return (
    <Card className="overflow-hidden border-slate-200/80 bg-slate-950 text-white shadow-lg shadow-slate-950/10">
      <CardContent className="p-5">
        <span className="inline-flex rounded-xl bg-white/10 p-2.5 text-indigo-200">
          <ShieldCheck aria-hidden="true" size={19} />
        </span>
        <h2 className="mt-5 text-lg font-semibold">You stay in control</h2>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          High-impact actions remain behind your approval. Review what FlowPilot can do and the apps
          it can access at any time.
        </p>
        <div className="mt-5 space-y-2 text-sm font-medium">
          <Link
            className="flex items-center justify-between rounded-lg bg-white/10 px-3 py-2.5 transition-colors hover:bg-white/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            href="/dashboard/settings/autonomy"
          >
            Manage permissions <ArrowRight aria-hidden="true" size={16} />
          </Link>
          <Link
            className="flex items-center justify-between rounded-lg px-3 py-2.5 text-slate-200 transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            href="/dashboard/connections"
          >
            Review app access <ArrowRight aria-hidden="true" size={16} />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export function LifeFeed() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const isLoading = useRef(false);

  const load = useCallback(async () => {
    if (isLoading.current) return;

    isLoading.current = true;
    setError(null);
    try {
      const [dashboard, events] = await Promise.all([
        api.getDashboardSummary(),
        api.listEvents({ limit: 10 }),
      ]);
      setSummary(dashboard);
      setItems(
        events.items.map((event) => ({
          event,
          status: event.latest_plan?.status ?? "received",
          plan: event.latest_plan,
        })),
      );
    } catch (caught) {
      if (
        typeof caught === "object" &&
        caught !== null &&
        "status" in caught &&
        (caught as { status?: unknown }).status === 401
      ) {
        return; // Let the auth client's redirect handle it without flashing an error state.
      }
      console.warn("Feed data could not be loaded:", caught);
      setError(caught);
    } finally {
      isLoading.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, 30_000);
    return () => clearInterval(timer);
  }, [load]);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl p-4 sm:p-6 lg:p-8">
        <LoadingSkeleton className="h-80" label="Loading your home page" />
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-7xl space-y-3 p-4 sm:p-6 lg:p-8">
        <ErrorState error={error} title="Your home page could not be loaded" />
        <Button onClick={() => void load()} type="button" variant="outline">
          Try again
        </Button>
      </main>
    );
  }

  const approvalsWaiting = summary?.pending_approvals ?? 0;
  return (
    <main className="mx-auto max-w-7xl p-4 pb-24 sm:p-6 md:pb-8 lg:p-8">
      <section className="relative overflow-hidden rounded-3xl bg-slate-950 px-5 py-7 text-white shadow-xl shadow-slate-900/10 sm:px-8 sm:py-9">
        <div
          aria-hidden="true"
          className="absolute -right-24 -top-28 h-72 w-72 rounded-full bg-indigo-500/25 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="absolute bottom-0 left-1/3 h-40 w-40 rounded-full bg-sky-400/10 blur-3xl"
        />
        <div className="relative flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-indigo-200">
              <Sparkles aria-hidden="true" size={14} /> Personal control centre
            </p>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">Your day</h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
              {approvalsWaiting
                ? `${approvalsWaiting} item${approvalsWaiting === 1 ? " is" : "s are"} ready for your decision. Everything else is organised below.`
                : "Everything important is in one calm, clear place. We’ll surface you only when your input matters."}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            {approvalsWaiting ? (
              <Button asChild className="bg-white text-slate-950 hover:bg-slate-100">
                <Link href="/dashboard/approvals">Review {approvalsWaiting} waiting</Link>
              </Button>
            ) : null}
            <Button
              asChild
              className="border-white/20 bg-white/10 text-white hover:bg-white/20"
              variant="outline"
            >
              <Link href="/dashboard/events">View activity</Link>
            </Button>
          </div>
        </div>
      </section>

      <section
        aria-label="Today at a glance"
        className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5"
      >
        {STAT_CARDS.map((item) => (
          <StatCard item={item} key={item.key} value={summary?.[item.key]} />
        ))}
      </section>

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-[minmax(0,1.65fr)_minmax(18rem,0.75fr)]">
        <section aria-label="Recent activity" className="min-w-0">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">
                Activity
              </p>
              <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">
                Latest signals
              </h2>
            </div>
            {items.length ? (
              <Link
                className="text-sm font-medium text-indigo-700 hover:text-indigo-900 hover:underline"
                href="/dashboard/events"
              >
                See all activity
              </Link>
            ) : null}
          </div>
          {items.length ? (
            <div className="space-y-3">
              {items.map((item) => (
                <FeedCard key={item.event.id} {...item} />
              ))}
            </div>
          ) : (
            <EmptyState
              action={
                <Button asChild>
                  <Link href="/events/new">Tell FlowPilot what happened</Link>
                </Button>
              }
              description="Connect an app or tell FlowPilot about an update to get started."
              title="You’re all caught up"
            />
          )}
        </section>
        <aside className="space-y-4" aria-label="Your controls">
          <ControlCard />
          <Card className="border-indigo-100 bg-indigo-50/60">
            <CardContent className="p-5">
              <p className="text-sm font-semibold text-slate-900">A clearer next step</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Keep routine work moving with automations that always follow your permission limits.
              </p>
              <Link
                className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:underline"
                href="/dashboard/standing-orders"
              >
                Explore automations <ArrowRight aria-hidden="true" size={15} />
              </Link>
            </CardContent>
          </Card>
        </aside>
      </div>
    </main>
  );
}
