import type { EventEntity, EventListItem } from "@/lib/api/types";

export const eventTypes = ["travel_booked", "travel_changed", "client_opportunity", "client_confirmed", "salary_credited", "subscription_renewal", "generic_important_event"] as const;

export function readable(value: string) { return value.replaceAll("_", " "); }
export function formatDate(value: string) { return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); }
export function maskValue(value: unknown) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  if (!text) return "Hidden";
  return text.length <= 4 ? "••••" : `••••${text.slice(-4)}`;
}
export function entityValue(entity: EventEntity, reveal = false) {
  const value = Object.entries(entity.value).map(([key, item]) => {
    const display = entity.is_sensitive && !reveal ? maskValue(item) : String(item);
    return `${key}: ${display}`;
  });
  return value.length ? value.join(", ") : entity.is_sensitive && !reveal ? "Hidden" : "No value";
}
export function eventMatchesSearch(event: EventListItem, query: string) {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return true;
  return [event.type, event.summary, ...event.entities.map((entity) => entity.kind)].join(" ").toLocaleLowerCase().includes(needle);
}
