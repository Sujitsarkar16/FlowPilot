"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  BadgeCheck,
  ChevronRight,
  CircleUserRound,
  LockKeyhole,
  PlugZap,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";

import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { Connection, CurrentUser, Preferences } from "@/lib/api/types";

type SettingsData = {
  user: CurrentUser;
  preferences: Preferences;
  connections: Connection[];
};

const autonomyLabels = {
  observe: "Watch only",
  suggest: "Ask me first",
  safe_actions: "Handle safe tasks",
} as const;

function userInitials(user: CurrentUser) {
  const source = user.display_name?.trim() || user.email?.trim() || "You";
  return source
    .split(/\s+|@/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

function SettingLink({
  description,
  href,
  icon: Icon,
  title,
}: {
  description: string;
  href: string;
  icon: typeof ShieldCheck;
  title: string;
}) {
  return (
    <Link
      className="group flex items-center gap-4 rounded-xl border border-slate-200/80 bg-white p-4 transition-all hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      href={href}
    >
      <span className="rounded-xl bg-indigo-50 p-2.5 text-indigo-700">
        <Icon aria-hidden="true" size={19} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-medium text-slate-900">{title}</span>
        <span className="mt-1 block text-sm leading-5 text-slate-600">{description}</span>
      </span>
      <ChevronRight
        aria-hidden="true"
        className="shrink-0 text-slate-400 transition-transform group-hover:translate-x-0.5"
        size={18}
      />
    </Link>
  );
}

export function SettingsManager() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [user, preferences, connections] = await Promise.all([
        api.getMe(),
        api.getPreferences(),
        api.listConnections(),
      ]);
      setData({ user, preferences, connections });
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl p-4 sm:p-6 lg:p-8">
        <LoadingSkeleton className="h-[34rem]" label="Loading your settings" />
      </main>
    );
  }

  if (!data) {
    return (
      <main className="mx-auto max-w-6xl space-y-3 p-4 sm:p-6 lg:p-8">
        <ErrorState
          error={error ?? new Error("Your settings are unavailable.")}
          title="Settings could not be loaded"
        />
        <button
          className="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-100"
          onClick={() => void load()}
          type="button"
        >
          Try again
        </button>
      </main>
    );
  }

  const { connections, preferences, user } = data;
  const connected = connections.filter((connection) => connection.status === "connected");
  const connectedScopes = connected.reduce(
    (total, connection) => total + connection.scopes.length,
    0,
  );
  const accountName = user.display_name || user.email || "Your account";
  const accountEmail = user.email || "No email address is available";

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 pb-24 sm:p-6 md:pb-8 lg:p-8">
      <header className="relative overflow-hidden rounded-3xl border border-indigo-100 bg-gradient-to-br from-indigo-50 via-white to-sky-50 px-5 py-7 sm:px-8 sm:py-8">
        <div
          aria-hidden="true"
          className="absolute -right-20 -top-20 h-56 w-56 rounded-full bg-indigo-200/50 blur-3xl"
        />
        <div className="relative">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-indigo-700">
            Account centre
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Settings</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Manage your account, permissions, and privacy choices from one clear place.
          </p>
        </div>
      </header>

      <section
        aria-labelledby="profile-heading"
        className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]"
      >
        <Card className="border-slate-200/80">
          <CardHeader className="p-5 pb-3">
            <CardTitle id="profile-heading" className="text-lg">
              Your details
            </CardTitle>
            <p className="text-sm leading-6 text-slate-600">
              The identity information attached to your FlowPilot account.
            </p>
          </CardHeader>
          <CardContent className="p-5 pt-3">
            <div className="flex items-center gap-4 rounded-xl bg-slate-50 p-4">
              <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-lg font-semibold text-white">
                {userInitials(user)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-slate-950">{accountName}</p>
                <p className="mt-1 truncate text-sm text-slate-600">{accountEmail}</p>
              </div>
              <BadgeCheck
                aria-hidden="true"
                className="ml-auto shrink-0 text-emerald-600"
                size={22}
              />
            </div>
            <dl className="mt-5 grid gap-4 border-t border-slate-100 pt-5 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Account ID</dt>
                <dd className="mt-1 break-all font-medium text-slate-800">{user.id}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Default assistance</dt>
                <dd className="mt-1 font-medium text-slate-800">
                  {autonomyLabels[user.default_autonomy]}
                </dd>
              </div>
            </dl>
            <p className="mt-5 text-xs leading-5 text-slate-500">
              Profile changes are managed by your sign-in provider. Your account identifier is shown
              here for support and privacy requests.
            </p>
          </CardContent>
        </Card>

        <Card className="border-slate-200/80 bg-slate-950 text-white">
          <CardContent className="p-5">
            <span className="inline-flex rounded-xl bg-white/10 p-2.5 text-indigo-200">
              <ShieldCheck aria-hidden="true" size={20} />
            </span>
            <h2 className="mt-5 text-lg font-semibold">Your safety snapshot</h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              FlowPilot is set to{" "}
              <strong className="font-semibold text-white">
                {autonomyLabels[preferences.autonomy_level]}
              </strong>
              .
            </p>
            <dl className="mt-5 grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-white/10 p-3">
                <dt className="text-xs text-slate-300">Connected apps</dt>
                <dd className="mt-1 text-2xl font-semibold">{connected.length}</dd>
              </div>
              <div className="rounded-xl bg-white/10 p-3">
                <dt className="text-xs text-slate-300">Granted scopes</dt>
                <dd className="mt-1 text-2xl font-semibold">{connectedScopes}</dd>
              </div>
            </dl>
            <Link
              className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-white hover:text-indigo-200 hover:underline"
              href="/dashboard/settings/autonomy"
            >
              Review permissions <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </CardContent>
        </Card>
      </section>

      <section aria-labelledby="controls-heading">
        <div className="mb-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">
            Control centre
          </p>
          <h2
            id="controls-heading"
            className="mt-1 text-xl font-semibold tracking-tight text-slate-950"
          >
            Your choices, clearly explained
          </h2>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <SettingLink
            description="Choose when FlowPilot watches, suggests, or handles safe tasks."
            href="/dashboard/settings/autonomy"
            icon={SlidersHorizontal}
            title="Automation permissions"
          />
          <SettingLink
            description={`${connected.length} app${connected.length === 1 ? "" : "s"} connected. Inspect each approved scope or disconnect at any time.`}
            href="/dashboard/connections"
            icon={PlugZap}
            title="Connected app access"
          />
          <SettingLink
            description="Read the plain-language security, privacy, and DPDP information notice."
            href="/dashboard/settings/privacy"
            icon={LockKeyhole}
            title="Privacy & data"
          />
        </div>
      </section>

      <section aria-labelledby="access-heading" className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Card className="border-slate-200/80">
          <CardHeader className="p-5 pb-3">
            <CardTitle id="access-heading" className="text-lg">
              App access at a glance
            </CardTitle>
            <p className="text-sm leading-6 text-slate-600">
              Only connected providers can share data with FlowPilot. The permissions below come
              directly from the connection record.
            </p>
          </CardHeader>
          <CardContent className="p-5 pt-3">
            {connected.length ? (
              <ul className="space-y-3">
                {connected.map((connection) => (
                  <li
                    className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"
                    key={connection.id}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium capitalize text-slate-900">
                        {connection.provider.replaceAll("_", " ")}
                      </p>
                      <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800">
                        Connected
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-5 text-slate-600">
                      {connection.scopes.length
                        ? `Granted: ${connection.scopes.join(", ")}`
                        : "This provider did not return individual scope names. Review it in Connected apps."}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm leading-6 text-slate-600">
                No apps are connected yet. FlowPilot cannot access an external account until you
                choose to connect one.
              </div>
            )}
            <Link
              className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:underline"
              href="/dashboard/connections"
            >
              Manage connected apps <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </CardContent>
        </Card>

        <Card className="border-emerald-100 bg-emerald-50/60">
          <CardContent className="p-5">
            <span className="inline-flex rounded-xl bg-emerald-100 p-2.5 text-emerald-700">
              <CircleUserRound aria-hidden="true" size={20} />
            </span>
            <h2 className="mt-4 text-lg font-semibold text-slate-950">Your data, your control</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              You can review app permissions, withdraw access by disconnecting an app, and change
              how FlowPilot acts on your behalf whenever you need to.
            </p>
            <Link
              className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-emerald-800 hover:underline"
              href="/dashboard/settings/privacy"
            >
              Understand your privacy choices <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
