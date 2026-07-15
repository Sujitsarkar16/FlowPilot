"use client";

import { useState } from "react";

type Section = "life-feed" | "orders" | "autonomy" | "graph" | "audit";

type PlanAction = {
  id: string;
  label: string;
  detail: string;
  connector: string;
  status: "verified" | "awaiting approval" | "proposed" | "blocked";
  risk: "safe" | "approval" | "policy";
};

const planActions: PlanAction[] = [
  {
    id: "ticket",
    label: "Save boarding pass",
    detail: "Travel / 2026 / Bengaluru",
    connector: "Drive",
    status: "verified",
    risk: "safe",
  },
  {
    id: "calendar",
    label: "Create calendar hold",
    detail: "Airport and boarding reminders included",
    connector: "Calendar",
    status: "verified",
    risk: "safe",
  },
  {
    id: "weather",
    label: "Prepare for the weather",
    detail: "Packing checklist is ready",
    connector: "Weather",
    status: "verified",
    risk: "safe",
  },
  {
    id: "family",
    label: "Send family itinerary",
    detail: "A draft is ready for your review",
    connector: "Messages",
    status: "awaiting approval",
    risk: "approval",
  },
];

const navItems: { id: Section; icon: string; label: string }[] = [
  { id: "life-feed", icon: "⌂", label: "Life Feed" },
  { id: "orders", icon: "⌘", label: "Standing Orders" },
  { id: "autonomy", icon: "◎", label: "Autonomy Centre" },
  { id: "graph", icon: "◇", label: "Personal Graph" },
  { id: "audit", icon: "≡", label: "Audit trail" },
];

const domains = [
  ["Calendar", "Calendar", "Automatic", "Meetings, holds, and reminders"],
  ["Files", "Drive", "Automatic", "Save and organise approved documents"],
  ["Drafting", "Drafts", "Automatic", "Prepare replies and summaries"],
  ["Messages", "Messages", "Ask every time", "Any external message needs approval"],
  ["Sharing", "Sharing", "Ask every time", "Review recipient and permissions"],
  ["Repositories", "GitHub", "Ask every time", "Private by default"],
  ["Finance", "Finance", "Never automatic", "Suggestions only — no money movement"],
] as const;

function Status({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "green" | "amber" | "neutral" | "red";
}) {
  return (
    <span className={`status status-${tone}`}>
      <span aria-hidden="true" />
      {children}
    </span>
  );
}

function Button({
  children,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" className={`button ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}

export default function LifeFeedPage() {
  const [activeSection, setActiveSection] = useState<Section>("life-feed");
  const [approved, setApproved] = useState(false);
  const [shadowMode, setShadowMode] = useState(false);
  const [showPlan, setShowPlan] = useState(true);
  const [ruleEnabled, setRuleEnabled] = useState(true);
  const [ruleSaved, setRuleSaved] = useState(false);
  const [draft, setDraft] = useState(
    "Whenever I book travel, prepare my itinerary and remind me about documents.",
  );
  const [budget, setBudget] = useState(12);
  const [domainModes, setDomainModes] = useState<Record<string, string>>({});

  const reviewPlan = () => {
    setActiveSection("life-feed");
    setShowPlan(true);
    window.setTimeout(
      () =>
        document
          .getElementById("plan-manifest")
          ?.scrollIntoView({ behavior: "smooth", block: "start" }),
      0,
    );
  };

  const setDomainMode = (name: string, mode: string) =>
    setDomainModes((current) => ({ ...current, [name]: mode }));

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <a className="brand" href="#top" aria-label="FlowPilot home">
            pulse<span>OS</span>
          </a>
          <button
            className="new-action"
            type="button"
            onClick={() => setActiveSection("orders")}
            aria-label="Create a standing order"
          >
            +
          </button>
        </div>
        <p className="workspace-label">Personal control centre</p>
        <nav className="primary-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${activeSection === item.id ? "active" : ""}`}
              onClick={() => setActiveSection(item.id)}
              aria-current={activeSection === item.id ? "page" : undefined}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-state">
            <span className="online-dot" aria-hidden="true" />
            <div>
              <strong>4 connected services</strong>
              <small>All systems operational</small>
            </div>
          </div>
          <button type="button" className="profile" aria-label="Open Sujit’s profile">
            <span className="avatar">S</span>
            <span>
              <strong>Sujit</strong>
              <small>Personal workspace</small>
            </span>
            <b aria-hidden="true">⌄</b>
          </button>
        </div>
      </aside>

      <section className="workspace" id="top">
        <header className="topbar">
          <div className="breadcrumb">
            <span className="online-dot" aria-hidden="true" />
            Workspace protected <span className="topbar-divider">/</span> Demo workspace
          </div>
          <div className="topbar-actions">
            <button
              type="button"
              className={`shadow-toggle ${shadowMode ? "on" : ""}`}
              onClick={() => setShadowMode((value) => !value)}
              aria-pressed={shadowMode}
            >
              <span aria-hidden="true" />
              Shadow mode
            </button>
            <button type="button" className="icon-button" aria-label="View notifications">
              ⌁<i>1</i>
            </button>
          </div>
        </header>

        {shadowMode && (
          <div className="shadow-banner" role="status">
            <span aria-hidden="true">◌</span>
            <div>
              <strong>Shadow mode is on</strong>
              <p>Plans are shown as usual, but no connector side effects will be requested.</p>
            </div>
            <Button className="button-quiet" onClick={() => setShadowMode(false)}>
              Exit shadow mode
            </Button>
          </div>
        )}

        {activeSection === "life-feed" && (
          <>
            <section className="hero" aria-labelledby="page-title">
              <div>
                <p className="eyebrow">Wednesday, 15 July</p>
                <h1 id="page-title">Good afternoon, Sujit.</h1>
                <p className="lede">
                  Your assistants have kept the important things moving — with you in control.
                </p>
              </div>
              <div className="control-note">
                <span aria-hidden="true">✦</span>
                <p>
                  <strong>Designed around your boundaries</strong>
                  <br />
                  External messages never leave without your approval.
                </p>
              </div>
            </section>

            <dl className="metric-grid" aria-label="Today’s FlowPilot summary">
              <div>
                <dt>Events handled</dt>
                <dd>3</dd>
                <small>Across 4 connected services</small>
              </div>
              <div>
                <dt>Needs approval</dt>
                <dd>{approved ? "0" : "1"}</dd>
                <small>{approved ? "All decisions are up to date" : "One message is ready"}</small>
              </div>
              <div>
                <dt>Time returned</dt>
                <dd>
                  8<span>h</span>
                </dd>
                <small>This month, based on completed tasks</small>
              </div>
              <div className="metric-trust">
                <dt>Autonomy</dt>
                <dd>
                  <Status tone="green">Level 2</Status>
                </dd>
                <small>Safe actions can run automatically</small>
              </div>
            </dl>

            <section className="section-intro">
              <div>
                <p className="eyebrow">Today</p>
                <h2>Life Feed</h2>
              </div>
              <div className="filter-group" aria-label="Life Feed filters">
                <button type="button" className="filter active">
                  All activity
                </button>
                <button type="button" className="filter">
                  Needs you
                </button>
              </div>
            </section>

            <section className="event-layout" aria-label="Today’s events">
              <article className="event-card featured-card" aria-labelledby="travel-title">
                <header className="event-header">
                  <div className="event-icon travel" aria-hidden="true">
                    ✈
                  </div>
                  <div className="event-title">
                    <p className="eyebrow">
                      Travel Autopilot <span className="event-source">Gmail</span>
                    </p>
                    <h2 id="travel-title">Trip to Bengaluru detected</h2>
                    <p>
                      Mumbai <b>→</b> Bengaluru <i>·</i> Sat, 19 Jul <i>·</i> 08:10 IST
                    </p>
                  </div>
                  <Status tone={approved ? "green" : "amber"}>
                    {approved ? "Complete" : "1 approval needed"}
                  </Status>
                </header>
                <div className="trip-summary">
                  <div>
                    <span className="flight-label">INDIGO 6E-123</span>
                    <strong>Travel plan prepared</strong>
                    <p>
                      Flight details were extracted with high confidence. Your PNR remains redacted.
                    </p>
                  </div>
                  <span className="confidence">
                    97%<small>confidence</small>
                  </span>
                </div>
                <ul className="action-list">
                  {planActions.slice(0, 3).map((action) => (
                    <li key={action.id}>
                      <span className="action-check" aria-hidden="true">
                        ✓
                      </span>
                      <div>
                        <strong>{action.label}</strong>
                        <small>{action.detail}</small>
                      </div>
                      <Status tone="green">Verified</Status>
                    </li>
                  ))}
                </ul>
                <footer className="card-footer">
                  <p>
                    <span aria-hidden="true">◷</span>
                    {approved
                      ? "Family itinerary update approved in this local preview."
                      : "One prepared family update is waiting for your decision."}
                  </p>
                  <Button className="button-secondary" onClick={reviewPlan}>
                    Review plan <span aria-hidden="true">→</span>
                  </Button>
                </footer>
              </article>

              <aside
                className={`approval-card ${approved ? "approved" : ""}`}
                aria-labelledby="approval-title"
              >
                <div className="attention-head">
                  <p className="eyebrow">{approved ? "Decision recorded" : "Your attention"}</p>
                  <Status tone={approved ? "green" : "amber"}>
                    {approved ? "Approved" : "Awaiting you"}
                  </Status>
                </div>
                <h2 id="approval-title">
                  {approved ? "Family update approved" : "One small decision"}
                </h2>
                <div className="message-preview">
                  <span className="contact-avatar" aria-hidden="true">
                    F
                  </span>
                  <div>
                    <strong>Family itinerary update</strong>
                    <p>“I’ll be in Bengaluru this Saturday…”</p>
                  </div>
                </div>
                <p className="approval-copy">
                  {approved
                    ? "The local demo has recorded your approval. A real API would now send this exact, versioned draft."
                    : "FlowPilot drafted this from your trip plan. It cannot send it until you approve the version shown here."}
                </p>
                {approved ? (
                  <Button className="button-secondary" onClick={() => setApproved(false)}>
                    Undo local decision
                  </Button>
                ) : (
                  <div className="decision-actions">
                    <Button className="button-primary" onClick={() => setApproved(true)}>
                      {shadowMode ? "Record approval" : "Approve message"}
                    </Button>
                    <Button className="button-text" onClick={() => setApproved(true)}>
                      Not now
                    </Button>
                  </div>
                )}
                <small className="boundary-note">
                  <span aria-hidden="true">⌘</span>{" "}
                  {shadowMode
                    ? "Shadow mode prevents any external side effect."
                    : "Messages are an approval-only action."}
                </small>
              </aside>
            </section>

            <section className="secondary-events" aria-label="Other active workflows">
              <article>
                <div className="event-icon client" aria-hidden="true">
                  ◫
                </div>
                <div>
                  <p className="eyebrow">
                    Client Launch <span className="event-source">Email</span>
                  </p>
                  <h3>Northstar project opportunity</h3>
                  <p>
                    Requirements and a private workspace are ready. The reply remains in drafts.
                  </p>
                </div>
                <Status tone="amber">Draft needs approval</Status>
                <Button className="button-link" onClick={reviewPlan}>
                  View plan →
                </Button>
              </article>
              <article>
                <div className="event-icon finance" aria-hidden="true">
                  ⌁
                </div>
                <div>
                  <p className="eyebrow">
                    Salary Autopilot <span className="event-source">Sandbox</span>
                  </p>
                  <h3>Salary plan is ready to review</h3>
                  <p>Budget suggestions were prepared. No transfer or purchase can be automated.</p>
                </div>
                <Status tone="neutral">Proposal only</Status>
                <Button className="button-link" onClick={() => setActiveSection("autonomy")}>
                  View safeguards →
                </Button>
              </article>
            </section>

            {showPlan && (
              <section
                className="plan-manifest"
                id="plan-manifest"
                aria-labelledby="manifest-title"
              >
                <div className="manifest-title">
                  <div>
                    <p className="eyebrow">
                      Plan manifest <span className="event-source">plan_bengaluru_001</span>
                    </p>
                    <h2 id="manifest-title">Prepare Bengaluru trip</h2>
                    <p>Every step, policy decision, and connector result stays visible.</p>
                  </div>
                  <button
                    type="button"
                    className="dismiss-button"
                    onClick={() => setShowPlan(false)}
                    aria-label="Collapse plan manifest"
                  >
                    ×
                  </button>
                </div>
                <div className="manifest-meta">
                  <span>
                    <b>4</b> actions
                  </span>
                  <span>
                    <b>1</b> approval
                  </span>
                  <span>
                    <b>5</b> services
                  </span>
                  <span>
                    <b>0</b> sensitive fields exposed
                  </span>
                </div>
                <ol className="plan-list">
                  {planActions.map((action, index) => (
                    <li key={action.id}>
                      <span className="step-number">{index + 1}</span>
                      <div className="plan-action">
                        <div>
                          <strong>{action.label}</strong>
                          <small>
                            {action.detail} · {action.connector}
                          </small>
                        </div>
                        <div className="plan-action-meta">
                          <Status tone={action.risk === "safe" ? "green" : "amber"}>
                            {action.status}
                          </Status>
                          <button
                            type="button"
                            className="why-button"
                            aria-label={`Why is ${action.label} included?`}
                          >
                            Why?
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
                <footer className="manifest-footer">
                  <p>
                    <span aria-hidden="true">✓</span> Policy checked against your Travel Autopilot
                    order.
                  </p>
                  <Button className="button-secondary" onClick={() => setActiveSection("audit")}>
                    Open audit trail
                  </Button>
                </footer>
              </section>
            )}

            <section className="timeline-section" aria-labelledby="timeline-title">
              <div className="section-intro">
                <div>
                  <p className="eyebrow">Execution timeline</p>
                  <h2 id="timeline-title">Everything stays visible</h2>
                </div>
                <Status tone="green">3 actions verified</Status>
              </div>
              <ol className="timeline">
                <li>
                  <time>09:30</time>
                  <span className="timeline-marker done" aria-hidden="true" />
                  <div>
                    <strong>Flight confirmation recognised</strong>
                    <p>Gmail event interpreted as Travel.Booked · 97% confidence</p>
                  </div>
                  <em>Gmail</em>
                </li>
                <li>
                  <time>09:31</time>
                  <span className="timeline-marker done" aria-hidden="true" />
                  <div>
                    <strong>Trip workspace and reminders prepared</strong>
                    <p>Ticket stored in your Travel folder and airport reminders created</p>
                  </div>
                  <em>Drive + Calendar</em>
                </li>
                <li>
                  <time>09:32</time>
                  <span
                    className={`timeline-marker ${approved ? "done" : "waiting"}`}
                    aria-hidden="true"
                  />
                  <div>
                    <strong>
                      {approved
                        ? "Family approval recorded"
                        : "Family itinerary is ready for approval"}
                    </strong>
                    <p>
                      {approved
                        ? "Demo decision recorded locally; no external message was sent."
                        : "The prepared message is blocked by your messaging policy."}
                    </p>
                  </div>
                  <em>{approved ? "Recorded" : "Messages"}</em>
                </li>
              </ol>
            </section>
          </>
        )}

        {activeSection === "orders" && (
          <section className="settings-page" aria-labelledby="orders-title">
            <div className="page-heading">
              <div>
                <p className="eyebrow">Policy builder</p>
                <h1 id="orders-title">Standing Orders</h1>
                <p className="lede">
                  Tell FlowPilot what should happen repeatedly. It always shows the resulting
                  boundaries before anything is saved.
                </p>
              </div>
              <Status tone="green">1 active order</Status>
            </div>
            <div className="orders-layout">
              <article className="rule-card">
                <div className="rule-card-heading">
                  <div>
                    <span className="rule-icon" aria-hidden="true">
                      ✈
                    </span>
                    <div>
                      <p className="eyebrow">Travel Autopilot</p>
                      <h2>Prepare every confirmed trip</h2>
                    </div>
                  </div>
                  <button
                    type="button"
                    className={`switch ${ruleEnabled ? "on" : ""}`}
                    onClick={() => setRuleEnabled((value) => !value)}
                    role="switch"
                    aria-checked={ruleEnabled}
                  >
                    <span />
                  </button>
                </div>
                <p>Whenever I book travel, prepare my itinerary and remind me about documents.</p>
                <div className="rule-tags">
                  <Status tone="green">Safe actions automatic</Status>
                  <Status tone="amber">Messages ask every time</Status>
                </div>
                <footer>
                  <span>
                    {ruleEnabled
                      ? "Enabled and policy checked"
                      : "Paused — no future plans will run"}
                  </span>
                  <Button className="button-text">Edit order</Button>
                </footer>
              </article>
              <article className="rule-builder">
                <p className="eyebrow">New standing order</p>
                <h2>From now on, whenever…</h2>
                <label htmlFor="rule-draft" className="sr-only">
                  Standing order instruction
                </label>
                <textarea
                  id="rule-draft"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  rows={3}
                />
                <div className="compiled-preview">
                  <div>
                    <span aria-hidden="true">⌘</span>
                    <div>
                      <strong>Compiled policy preview</strong>
                      <p>
                        Trigger: travel confirmation · Safe actions: calendar, files, drafting ·
                        Approval: external messages
                      </p>
                    </div>
                  </div>
                  <Status tone="green">No money movement</Status>
                </div>
                <footer>
                  <small>
                    {ruleSaved
                      ? "Draft saved in this local preview."
                      : "Saving creates a policy draft for review — it does not run anything."}
                  </small>
                  <Button className="button-primary" onClick={() => setRuleSaved(true)}>
                    Save policy draft
                  </Button>
                </footer>
              </article>
            </div>
            <section className="explain-card">
              <span aria-hidden="true">✦</span>
              <div>
                <h2>What gets checked before every plan?</h2>
                <p>
                  FlowPilot compares the event, current standing order, domain permission, budget, and
                  any approval requirement. A plan is blocked when one of those checks does not
                  pass.
                </p>
              </div>
              <Button className="button-secondary" onClick={() => setActiveSection("audit")}>
                See policy decisions
              </Button>
            </section>
          </section>
        )}

        {activeSection === "autonomy" && (
          <section className="settings-page" aria-labelledby="autonomy-title">
            <div className="page-heading">
              <div>
                <p className="eyebrow">Safety controls</p>
                <h1 id="autonomy-title">Autonomy Centre</h1>
                <p className="lede">
                  Choose where FlowPilot can help automatically, and where it should always ask first.
                </p>
              </div>
              <Status tone="green">Level 2 autonomy</Status>
            </div>
            <section className="autonomy-summary">
              <div>
                <p className="eyebrow">Daily autonomy budget</p>
                <h2>{budget} actions available today</h2>
                <p>
                  Safe connector actions consume your daily budget. Approval-only and blocked
                  actions do not.
                </p>
                <input
                  id="budget"
                  type="range"
                  min="4"
                  max="20"
                  value={budget}
                  onChange={(event) => setBudget(Number(event.target.value))}
                  aria-label="Daily autonomy budget"
                />
                <div className="range-labels">
                  <span>4</span>
                  <span>20 safe actions</span>
                </div>
              </div>
              <div className="privacy-panel">
                <span aria-hidden="true">⌘</span>
                <h3>Safe by default</h3>
                <p>
                  Finance is never automatic. Messages, sharing, and repositories preserve their own
                  approval boundaries.
                </p>
                <Button className="button-secondary" onClick={() => setShadowMode(true)}>
                  Try shadow mode
                </Button>
              </div>
            </section>
            <section className="domain-grid" aria-label="Autonomy settings by domain">
              {domains.map(([name, service, defaultMode, detail]) => {
                const mode = domainModes[name] ?? defaultMode;
                return (
                  <article key={name} className={name === "Finance" ? "finance-domain" : ""}>
                    <header>
                      <div>
                        <p className="eyebrow">{service}</p>
                        <h2>{name}</h2>
                      </div>
                      <Status
                        tone={
                          mode === "Automatic"
                            ? "green"
                            : mode === "Never automatic"
                              ? "red"
                              : "amber"
                        }
                      >
                        {mode}
                      </Status>
                    </header>
                    <p>{detail}</p>
                    <div className="segmented" role="group" aria-label={`${name} autonomy level`}>
                      {["Automatic", "Ask every time", "Never automatic"].map((option) => (
                        <button
                          key={option}
                          type="button"
                          disabled={name === "Finance" && option !== "Never automatic"}
                          className={mode === option ? "selected" : ""}
                          onClick={() => setDomainMode(name, option)}
                        >
                          {option === "Ask every time"
                            ? "Ask"
                            : option === "Never automatic"
                              ? "Never"
                              : "Auto"}
                        </button>
                      ))}
                    </div>
                  </article>
                );
              })}
            </section>
            <section className="trusted-contacts">
              <div>
                <p className="eyebrow">Trusted contacts</p>
                <h2>Family messages stay in your hands</h2>
                <p>
                  FlowPilot can draft updates for your Family group, but every send is still an
                  explicit approval.
                </p>
              </div>
              <div className="contact-stack">
                <span>F</span>
                <span>M</span>
                <span>A</span>
              </div>
              <Button className="button-secondary">Manage trusted contacts</Button>
            </section>
          </section>
        )}

        {activeSection === "graph" && (
          <section className="settings-page" aria-labelledby="graph-title">
            <div className="page-heading">
              <div>
                <p className="eyebrow">Permission-aware context</p>
                <h1 id="graph-title">Personal Graph</h1>
                <p className="lede">
                  A small, private map of the people and projects you have allowed FlowPilot to use as
                  context.
                </p>
              </div>
              <Status tone="neutral">7 visible connections</Status>
            </div>
            <section className="graph-card">
              <div className="graph-toolbar">
                <p>
                  <span className="online-dot" />
                  Limited to approved context
                </p>
                <Button className="button-secondary">Manage permissions</Button>
              </div>
              <div
                className="graph-stage"
                role="img"
                aria-label="A graph linking Sujit to family, a Bengaluru trip, Northstar project, personal goals, and calendar"
              >
                <span className="graph-line line-one" />
                <span className="graph-line line-two" />
                <span className="graph-line line-three" />
                <span className="graph-line line-four" />
                <button className="graph-node you">
                  S<span>You</span>
                </button>
                <button className="graph-node family">
                  F<span>Family</span>
                </button>
                <button className="graph-node trip">
                  ✈<span>Bengaluru trip</span>
                </button>
                <button className="graph-node work">
                  N<span>Northstar</span>
                </button>
                <button className="graph-node goals">
                  ◎<span>Goals</span>
                </button>
                <button className="graph-node calendar">
                  □<span>Calendar</span>
                </button>
              </div>
              <footer>
                <p>
                  <span aria-hidden="true">⌘</span> This view never reveals private source data or
                  adds new permissions.
                </p>
                <Button className="button-text">How context is used →</Button>
              </footer>
            </section>
            <section className="context-table">
              <div>
                <p className="eyebrow">Context permissions</p>
                <h2>What FlowPilot can reference</h2>
              </div>
              <div className="table-rows">
                <div>
                  <span>Family</span>
                  <span>Draft itinerary updates</span>
                  <Status tone="amber">Approval required</Status>
                </div>
                <div>
                  <span>Northstar</span>
                  <span>Private project preparation</span>
                  <Status tone="green">Workspace only</Status>
                </div>
                <div>
                  <span>Personal goals</span>
                  <span>Planning suggestions</span>
                  <Status tone="neutral">Read-only</Status>
                </div>
              </div>
            </section>
          </section>
        )}

        {activeSection === "audit" && (
          <section className="settings-page" aria-labelledby="audit-title">
            <div className="page-heading">
              <div>
                <p className="eyebrow">Append-only history</p>
                <h1 id="audit-title">Audit trail</h1>
                <p className="lede">
                  A readable record of what was detected, decided, prepared, and verified.
                </p>
              </div>
              <Button className="button-secondary">Export local view</Button>
            </div>
            <section className="audit-summary">
              <div>
                <strong>Today’s activity</strong>
                <span>7 ledger entries</span>
              </div>
              <div>
                <strong>Current policy</strong>
                <span>Travel Autopilot · version 3</span>
              </div>
              <div>
                <strong>Last decision</strong>
                <span>
                  {approved ? "Message approval recorded locally" : "No decision recorded"}
                </span>
              </div>
            </section>
            <ol className="audit-list">
              <li>
                <time>09:32:18</time>
                <span className="audit-type policy">Policy</span>
                <div>
                  <strong>Family itinerary requires approval</strong>
                  <p>
                    Messaging domain is set to “Ask every time”. The plan was blocked before any
                    send request.
                  </p>
                </div>
                <Button className="button-text">Why?</Button>
              </li>
              <li>
                <time>09:31:44</time>
                <span className="audit-type verified">Verified</span>
                <div>
                  <strong>Weather checklist prepared</strong>
                  <p>
                    Weather connector returned successfully and the output was stored in the trip
                    workspace.
                  </p>
                </div>
                <Button className="button-text">View output</Button>
              </li>
              <li>
                <time>09:31:09</time>
                <span className="audit-type verified">Verified</span>
                <div>
                  <strong>Calendar reminders created</strong>
                  <p>
                    Airport and boarding reminders were verified against the Calendar connector
                    response.
                  </p>
                </div>
                <Button className="button-text">Undo</Button>
              </li>
              <li>
                <time>09:30:02</time>
                <span className="audit-type event">Event</span>
                <div>
                  <strong>Flight confirmation received</strong>
                  <p>
                    Gmail evidence was treated as untrusted input and extracted into redacted travel
                    facts.
                  </p>
                </div>
                <Button className="button-text">View facts</Button>
              </li>
            </ol>
          </section>
        )}
      </section>
    </main>
  );
}
