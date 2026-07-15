import { EmptyState } from "@/components/empty-state";

export default function EventsPage() {
  return (
    <div className="p-4 sm:p-6">
      <EmptyState
        description="Incoming events will appear here after a connection or manual event is added."
        title="No events yet"
      />
    </div>
  );
}
