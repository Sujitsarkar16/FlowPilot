import { ApiError, technicalErrorMessage, validationMessage } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

export function ErrorState({
  error,
  title = "We could not load this information.",
  className,
}: {
  error: unknown;
  title?: string;
  className?: string;
}) {
  const message =
    error instanceof ApiError
      ? (validationMessage(error.detail) ?? error.message)
      : error instanceof Error
        ? error.message
        : "Please try again.";
  return (
    <section
      className={cn("rounded-xl border border-red-200 bg-red-50 p-5 text-red-950", className)}
      role="alert"
    >
      <h2 className="font-semibold">{title}</h2>
      <p className="mt-1 text-sm">{message}</p>
      {error instanceof ApiError && error.requestId ? (
        <p className="mt-2 text-sm">Request ID: {error.requestId}</p>
      ) : null}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer">Technical details</summary>
        <p className="mt-1">{technicalErrorMessage(error)}</p>
      </details>
    </section>
  );
}
