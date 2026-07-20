import { EventDetail } from "@/features/events/event-detail";

export default async function EventWorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EventDetail eventId={id} workspace />;
}
