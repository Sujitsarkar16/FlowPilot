import type { EventEntity, EventListItem } from "@/lib/api/types";

export const MAX_EVENT_ATTACHMENTS = 20;
export const MAX_EVENT_ATTACHMENT_BYTES = 5 * 1024 * 1024;
export const EVENT_ATTACHMENT_ACCEPT =
  ".pdf,.docx,.png,.jpg,.jpeg,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/jpeg,image/png,text/plain,text/markdown";
const ACCEPTED_ATTACHMENT_TYPES = new Set([
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/jpeg",
  "image/png",
  "text/markdown",
  "text/plain",
]);
const MIME_BY_EXTENSION: Record<string, string> = {
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  md: "text/markdown",
  pdf: "application/pdf",
  png: "image/png",
  txt: "text/plain",
};

export function attachmentMimeType(file: File) {
  const extension = file.name.split(".").at(-1)?.toLocaleLowerCase();
  return file.type || (extension ? MIME_BY_EXTENSION[extension] : "") || "application/octet-stream";
}

export function attachmentIsValid(file: File) {
  return (
    file.size <= MAX_EVENT_ATTACHMENT_BYTES &&
    ACCEPTED_ATTACHMENT_TYPES.has(attachmentMimeType(file))
  );
}

export function attachmentBase64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("The attachment could not be read."));
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.readAsDataURL(file);
  });
}

export const eventTypes = [
  "travel_booked",
  "travel_changed",
  "client_opportunity",
  "client_confirmed",
  "salary_credited",
  "subscription_renewal",
  "generic_important_event",
] as const;

export function readable(value: string) {
  return value.replace(/[._]/g, " ");
}
export function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
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
  return [event.type, event.summary, ...event.entities.map((entity) => entity.kind)]
    .join(" ")
    .toLocaleLowerCase()
    .includes(needle);
}
