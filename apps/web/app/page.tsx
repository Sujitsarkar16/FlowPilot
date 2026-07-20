import type { Metadata } from "next";
import Image from "next/image";
import {
  ArrowRight,
  Check,
  ChevronRight,
  CircleCheckBig,
  Clock3,
  CreditCard,
  FileCheck2,
  Github,
  LockKeyhole,
  Mail,
  Network,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";

export const metadata: Metadata = {
  title: "FlowPilot | Automate with confidence",
  description:
    "FlowPilot gives every automation a clear approval path, a live activity feed, and a home your team can trust.",
};

const features = [
  {
    icon: ShieldCheck,
    title: "Safety by default",
    description:
      "Set the boundaries once. FlowPilot asks for approval whenever an automation reaches a decision that matters.",
  },
  {
    icon: Network,
    title: "One connected workspace",
    description:
      "Bring the services that run your day into a single, calm control centre—without giving up visibility.",
  },
  {
    icon: Clock3,
    title: "A complete activity trail",
    description:
      "See what ran, why it ran, and what happened next. Every action has context your team can follow.",
  },
];

const steps = [
  {
    number: "01",
    title: "Connect your tools",
    description: "Link the services you already use in a few guided, secure steps.",
  },
  {
    number: "02",
    title: "Set your guardrails",
    description: "Choose which workflows run freely and which ones should pause for review.",
  },
  {
    number: "03",
    title: "Stay in the loop",
    description: "Watch your feed, approve the important moments, and move on with confidence.",
  },
];

const useCases = [
  {
    icon: Mail,
    title: "Turn signals into action",
    description:
      "Bring in requests and updates from connected tools, then turn them into a clear plan instead of another notification.",
  },
  {
    icon: Clock3,
    title: "Run repeatable routines",
    description:
      "Create standing orders for recurring work while keeping the context, status, and next step visible in one place.",
  },
  {
    icon: CreditCard,
    title: "Pause at important decisions",
    description:
      "Route sensitive or high-impact actions to review so the routine work moves quickly without giving up control.",
  },
];

const safetyPoints = [
  "Preview the proposed steps before consequential work runs.",
  "Require approval when an action crosses your chosen boundary.",
  "See the reason, status, and outcome for every action in the activity feed.",
  "Adjust autonomy rules as your workflows and confidence evolve.",
];

function BrandMark({ priority = false }: { priority?: boolean }) {
  return (
    <Image
      alt="FlowPilot"
      className="h-[140px] w-[140px] object-contain"
      height={120}
      priority={priority}
      src="/flowpilot-logo.png"
      width={120}
    />
  );
}

export default function HomePage() {
  return (
    <main className="overflow-hidden bg-white text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-100 bg-white/90 backdrop-blur-lg overflow-visible">
        <nav
          className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-8"
          aria-label="Main navigation"
        >
          <a href="#top" className="flex items-center" aria-label="FlowPilot home">
            <BrandMark priority />
          </a>
          <div className="hidden items-center gap-7 text-sm font-medium text-slate-600 md:flex">
            <a className="transition hover:text-indigo-600" href="#features">
              Features
            </a>
            <a className="transition hover:text-indigo-600" href="#how-it-works">
              How it works
            </a>
            <a className="transition hover:text-indigo-600" href="#use-cases">
              Use cases
            </a>
            <a className="transition hover:text-indigo-600" href="#contact">
              Contact
            </a>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <a
              className="hidden text-sm font-semibold text-slate-700 transition hover:text-indigo-600 sm:block"
              href="/login?returnTo=%2Fdashboard"
            >
              Sign in
            </a>
            <a
              className="inline-flex h-10 items-center justify-center rounded-lg bg-indigo-600 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
              href="/login?returnTo=%2Fdashboard"
            >
              Get started <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden="true" />
            </a>
          </div>
        </nav>
      </header>

      <section id="top" className="relative isolate">
        <div className="absolute inset-x-0 top-0 -z-10 h-[630px] bg-[radial-gradient(circle_at_50%_0%,#e0e7ff_0%,#ffffff_62%)]" />
        <div className="mx-auto max-w-7xl px-5 pb-16 pt-20 sm:px-8 sm:pb-24 sm:pt-28 lg:pt-32">
          <div className="mx-auto max-w-3xl text-center">
            <p className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white px-3.5 py-1.5 text-sm font-semibold text-indigo-700 shadow-sm">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              The calmer way to automate
            </p>
            <h1 className="mt-7 text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-6xl lg:text-7xl">
              Your life moves fast.
              <span className="block text-indigo-600">Your automations should move wisely.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
              FlowPilot brings your connected tools, standing orders, and high-stakes decisions into
              one beautifully clear control centre.
            </p>
            <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
              <a
                className="inline-flex h-12 items-center justify-center rounded-lg bg-indigo-600 px-5 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:-translate-y-0.5 hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                href="/login?returnTo=%2Fdashboard"
              >
                Create your workspace <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
              </a>
              <a
                className="inline-flex h-12 items-center justify-center rounded-lg border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                href="#how-it-works"
              >
                See how it works <ChevronRight className="ml-1 h-4 w-4" aria-hidden="true" />
              </a>
            </div>
            <p className="mt-4 text-sm text-slate-500">Start free. No credit card required.</p>
          </div>

          <div className="relative mx-auto mt-16 max-w-5xl rounded-2xl border border-slate-200 bg-white p-2 shadow-2xl shadow-indigo-100/70 sm:p-3">
            <div className="overflow-hidden rounded-xl border border-slate-100 bg-slate-50">
              <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-300" />
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
                </div>
                <span className="text-xs font-medium text-slate-400">Your control centre</span>
                <span className="w-12" />
              </div>
              <div className="grid gap-4 p-4 sm:grid-cols-[170px_1fr] sm:gap-6 sm:p-6">
                <aside className="hidden rounded-lg bg-slate-900 p-4 text-slate-300 sm:block">
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <BrandMark />
                  </div>
                  <div className="mt-8 space-y-2 text-xs font-medium">
                    <p className="rounded-md bg-white/10 px-3 py-2.5 text-white">Life feed</p>
                    <p className="px-3 py-2.5">Approvals</p>
                    <p className="px-3 py-2.5">Connections</p>
                    <p className="px-3 py-2.5">Standing orders</p>
                  </div>
                </aside>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">Good morning, Alex</p>
                      <p className="mt-1 text-xs text-slate-500">
                        Here&apos;s what your workflows are doing today.
                      </p>
                    </div>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> All systems
                      normal
                    </span>
                  </div>
                  <div className="mt-5 grid gap-3 sm:grid-cols-3">
                    {[
                      ["12", "Actions completed"],
                      ["1", "Needs your approval"],
                      ["4", "Active connections"],
                    ].map(([value, label]) => (
                      <div
                        key={label}
                        className="rounded-lg border border-slate-200 bg-white p-3.5"
                      >
                        <p className="text-xl font-semibold tracking-tight text-slate-950">
                          {value}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">{label}</p>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50/60 p-4">
                    <div className="flex gap-3">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-indigo-600 shadow-sm">
                        <CreditCard className="h-4 w-4" aria-hidden="true" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-slate-900">
                            Review new subscription
                          </p>
                          <span className="text-xs text-slate-500">Just now</span>
                        </div>
                        <p className="mt-1 text-xs leading-5 text-slate-600">
                          A $24.00 monthly charge is ready for your approval.
                        </p>
                        <div className="mt-3 flex gap-2">
                          <span className="rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-semibold text-white">
                            Review
                          </span>
                          <span className="rounded-md bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 ring-1 ring-slate-200">
                            Dismiss
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
                    <CircleCheckBig
                      className="h-4 w-4 shrink-0 text-emerald-500"
                      aria-hidden="true"
                    />
                    <p className="text-xs text-slate-600">
                      <span className="font-semibold text-slate-800">Calendar brief sent</span> to
                      your inbox automatically.
                    </p>
                    <span className="ml-auto text-xs text-slate-400">9:00 AM</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-slate-100 bg-slate-50 py-7">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-x-10 gap-y-3 px-5 text-center text-sm font-medium text-slate-500 sm:px-8">
          <span className="inline-flex items-center gap-2">
            <LockKeyhole className="h-4 w-4 text-indigo-500" /> Secure by design
          </span>
          <span className="inline-flex items-center gap-2">
            <FileCheck2 className="h-4 w-4 text-indigo-500" /> Every action explained
          </span>
          <span className="inline-flex items-center gap-2">
            <Zap className="h-4 w-4 text-indigo-500" /> Built for everyday flow
          </span>
        </div>
      </section>

      <section id="features" className="scroll-mt-20 px-5 py-20 sm:px-8 sm:py-28">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-600">
              Built for trust
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              Automation you can actually feel good about.
            </h2>
            <p className="mt-5 text-lg leading-8 text-slate-600">
              Less tab switching. Less second guessing. More space to focus on what matters.
            </p>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {features.map(({ icon: Icon, title, description }) => (
              <article
                key={title}
                className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm transition hover:-translate-y-1 hover:shadow-lg hover:shadow-slate-200/60"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 text-lg font-semibold text-slate-950">{title}</h3>
                <p className="mt-3 leading-7 text-slate-600">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="scroll-mt-20 bg-slate-950 px-5 py-20 text-white sm:px-8 sm:py-28"
      >
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-end">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-300">
                How it works
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-5xl">
                A better system in three simple moves.
              </h2>
              <p className="mt-5 max-w-lg text-lg leading-8 text-slate-300">
                Start with the tools you know. Then let FlowPilot make the repeatable parts feel
                effortless.
              </p>
              <a
                className="mt-8 inline-flex items-center text-sm font-semibold text-white transition hover:text-indigo-300"
                href="/login?returnTo=%2Fdashboard"
              >
                Start your workspace <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
              </a>
            </div>
            <ol className="grid gap-4 sm:grid-cols-3">
              {steps.map((step) => (
                <li
                  key={step.number}
                  className="rounded-2xl border border-white/10 bg-white/[0.06] p-6"
                >
                  <p className="text-sm font-semibold text-indigo-300">{step.number}</p>
                  <h3 className="mt-8 text-lg font-semibold">{step.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{step.description}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      <section
        id="use-cases"
        className="scroll-mt-20 bg-slate-50 px-5 py-20 sm:px-8 sm:py-28"
      >
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-600">
              Built for real routines
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              Move work forward without losing the human context.
            </h2>
            <p className="mt-5 text-lg leading-8 text-slate-600">
              FlowPilot coordinates the work between your tools: collecting signals, preparing a
              plan, applying your standing instructions, and bringing you in when judgment matters.
            </p>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {useCases.map(({ icon: Icon, title, description }) => (
              <article key={title} className="rounded-2xl border border-slate-200 bg-white p-7">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 text-lg font-semibold text-slate-950">{title}</h3>
                <p className="mt-3 leading-7 text-slate-600">{description}</p>
              </article>
            ))}
          </div>
          <div className="mt-10 grid overflow-hidden rounded-3xl bg-slate-950 text-white shadow-xl lg:grid-cols-[0.9fr_1.1fr]">
            <div className="p-8 sm:p-10 lg:p-12">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-300">
                Control at every step
              </p>
              <h3 className="mt-3 text-2xl font-semibold tracking-tight sm:text-4xl">
                Autonomy that stays accountable.
              </h3>
              <p className="mt-5 leading-7 text-slate-300">
                You decide where FlowPilot can act and where it must ask. Plans stay explainable,
                approvals stay explicit, and completed work stays easy to audit.
              </p>
            </div>
            <ul className="grid gap-3 border-t border-white/10 bg-white/[0.04] p-8 sm:p-10 lg:border-l lg:border-t-0 lg:p-12">
              {safetyPoints.map((point) => (
                <li key={point} className="flex gap-3 text-sm leading-6 text-slate-200">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-indigo-300">
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                  {point}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section id="contact" className="scroll-mt-20 px-5 py-20 sm:px-8 sm:py-28">
        <div className="mx-auto max-w-5xl rounded-3xl bg-indigo-600 px-6 py-12 text-center text-white shadow-2xl shadow-indigo-200 sm:px-12 sm:py-16">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-200">
            Ready when you are
          </p>
          <h2 className="mx-auto mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-5xl">
            Give your automations a trusted home.
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-indigo-100">
            Set up your workspace in minutes, or get in touch to talk through the workflows that
            matter most.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <a
              className="inline-flex h-12 items-center justify-center rounded-lg bg-white px-5 text-sm font-semibold text-indigo-700 shadow-sm transition hover:bg-indigo-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              href="/login?returnTo=%2Fdashboard"
            >
              Start for free <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
            </a>
            <a
              className="inline-flex h-12 items-center justify-center rounded-lg border border-indigo-400 px-5 text-sm font-semibold text-white transition hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              href="mailto:hello@flowpilot.app"
            >
              <Mail className="mr-2 h-4 w-4" aria-hidden="true" /> Contact us
            </a>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-200 px-5 py-10 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-7 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center">
            <BrandMark />
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-slate-500">
            <a className="transition hover:text-indigo-600" href="#features">
              Features
            </a>
            <a className="transition hover:text-indigo-600" href="#use-cases">
              Use cases
            </a>
            <a className="transition hover:text-indigo-600" href="mailto:hello@flowpilot.app">
              Contact
            </a>
            <a
              className="inline-flex items-center gap-1.5 transition hover:text-indigo-600"
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
            >
              <Github className="h-4 w-4" aria-hidden="true" /> GitHub
            </a>
          </div>
          <p className="text-sm text-slate-400">
            © {new Date().getFullYear()} FlowPilot. Move wisely.
          </p>
        </div>
      </footer>
    </main>
  );
}
