import { Suspense } from "react";

import { EventsList } from "@/features/events/events-list";

export default function EventsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-600">Loading events…</div>}>
      <EventsList />
    </Suspense>
  );
}
