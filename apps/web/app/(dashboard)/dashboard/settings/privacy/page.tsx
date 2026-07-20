import Link from "next/link";
import { ArrowRight, CheckCircle2, LockKeyhole, ShieldCheck, UserRoundCheck } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const dataUses = [
  {
    title: "Account information",
    description:
      "Your account identifier and email or display name help identify your FlowPilot workspace and provide support.",
  },
  {
    title: "Connected-app data",
    description:
      "Only the information covered by the permissions you grant to a connected app is used to provide the requested workflow.",
  },
  {
    title: "Instructions and activity",
    description:
      "Your requests, events, and action history let FlowPilot prepare, explain, and track work for you.",
  },
];

const safeguards = [
  "Connection credentials are not displayed in this product interface.",
  "You can inspect granted app scopes and disconnect a provider whenever you choose.",
  "High-impact actions stay behind approval and policy controls.",
  "Access is designed around the minimum permissions an enabled workflow needs.",
];

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 pb-24 sm:p-6 md:pb-8 lg:p-8">
      <header className="relative overflow-hidden rounded-3xl bg-slate-950 px-5 py-8 text-white sm:px-8 sm:py-10">
        <div
          aria-hidden="true"
          className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-indigo-500/30 blur-3xl"
        />
        <div className="relative max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-indigo-200">
            Privacy & security notice
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Clear data choices, always within reach.
          </h1>
          <p className="mt-4 text-sm leading-6 text-slate-300 sm:text-base">
            This notice explains what FlowPilot may use, why it may use it, and the controls you
            have over connected apps and automated actions.
          </p>
        </div>
      </header>

      <Card className="border-amber-200 bg-amber-50/70">
        <CardContent className="flex gap-3 p-5 text-sm leading-6 text-slate-700">
          <ShieldCheck aria-hidden="true" className="mt-0.5 shrink-0 text-amber-700" size={20} />
          <p>
            This is an in-product transparency notice designed around the Digital Personal Data
            Protection Act, 2023 (DPDP Act) principles. Have your privacy team review and approve it
            before relying on it as your organisation’s formal legal notice or a statement of legal
            compliance.
          </p>
        </CardContent>
      </Card>

      <section aria-labelledby="data-heading">
        <div className="mb-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">
            Notice at a glance
          </p>
          <h2
            id="data-heading"
            className="mt-1 text-xl font-semibold tracking-tight text-slate-950"
          >
            What FlowPilot may process
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {dataUses.map((item) => (
            <Card className="border-slate-200/80" key={item.title}>
              <CardHeader className="p-5 pb-2">
                <CardTitle className="text-base">{item.title}</CardTitle>
              </CardHeader>
              <CardContent className="p-5 pt-2 text-sm leading-6 text-slate-600">
                {item.description}
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="access-heading" className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-slate-200/80">
          <CardHeader className="p-5 pb-3">
            <CardTitle id="access-heading" className="flex items-center gap-2 text-lg">
              <LockKeyhole aria-hidden="true" className="text-indigo-700" size={19} /> App access is
              permission-based
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-3 text-sm leading-6 text-slate-600">
            <p>
              Connecting an app does not give FlowPilot unrestricted access. Each provider shares
              only the permissions you approve during connection, and the exact granted scopes are
              shown in Connected apps.
            </p>
            <p>
              Disconnecting a provider withdraws FlowPilot’s access to that connected account. You
              can reconnect later if you choose.
            </p>
            <Link
              className="inline-flex items-center gap-1 font-medium text-indigo-700 hover:underline"
              href="/dashboard/connections"
            >
              Inspect connected app access <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </CardContent>
        </Card>

        <Card className="border-indigo-100 bg-indigo-50/60">
          <CardContent className="p-5">
            <span className="inline-flex rounded-xl bg-indigo-100 p-2.5 text-indigo-700">
              <UserRoundCheck aria-hidden="true" size={20} />
            </span>
            <h2 className="mt-4 text-lg font-semibold text-slate-950">Your consent and controls</h2>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
              <li>Choose which providers to connect and which permissions to grant.</li>
              <li>Change automation behaviour or daily limits before FlowPilot acts.</li>
              <li>Withdraw connected-app access at any time by disconnecting the provider.</li>
              <li>Review actions that need your explicit approval.</li>
            </ul>
            <Link
              className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:underline"
              href="/dashboard/settings/autonomy"
            >
              Manage automation permissions <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </CardContent>
        </Card>
      </section>

      <section aria-labelledby="security-heading">
        <Card className="border-slate-200/80">
          <CardHeader className="p-5 pb-3">
            <CardTitle id="security-heading" className="flex items-center gap-2 text-lg">
              <ShieldCheck aria-hidden="true" className="text-emerald-700" size={19} /> Security
              commitments in the product
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 p-5 pt-3 sm:grid-cols-2">
            {safeguards.map((safeguard) => (
              <p className="flex gap-2 text-sm leading-6 text-slate-600" key={safeguard}>
                <CheckCircle2
                  aria-hidden="true"
                  className="mt-1 shrink-0 text-emerald-600"
                  size={16}
                />
                {safeguard}
              </p>
            ))}
          </CardContent>
        </Card>
      </section>

      <section aria-labelledby="dpdp-heading">
        <Card className="border-slate-200/80">
          <CardHeader className="p-5 pb-3">
            <CardTitle id="dpdp-heading" className="text-lg">
              DPDP Act rights and request guidance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 p-5 pt-3 text-sm leading-6 text-slate-600">
            <p>
              Depending on how your organisation uses FlowPilot and the applicable law, you may have
              rights to understand processing, seek correction or erasure, withdraw consent, and
              raise a grievance. The account information in Settings helps your organisation locate
              the right record for a request.
            </p>
            <p>
              FlowPilot’s in-product controls let you review connected access and withdraw it
              directly. For data-access, correction, erasure, or grievance requests beyond those
              controls, use your organisation’s designated privacy or support channel and include
              your account ID.
            </p>
            <Link
              className="inline-flex items-center gap-1 font-medium text-indigo-700 hover:underline"
              href="/dashboard/settings"
            >
              Return to account settings <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
