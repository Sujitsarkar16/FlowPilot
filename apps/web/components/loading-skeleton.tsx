import { cn } from "@/lib/utils";

export function LoadingSkeleton({
  className,
  label = "Loading content",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <div aria-live="polite" className={cn("space-y-3", className)} role="status">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="h-5 w-2/5 animate-pulse rounded bg-slate-200" />
      <div aria-hidden="true" className="h-4 animate-pulse rounded bg-slate-200" />
      <div aria-hidden="true" className="h-4 w-4/5 animate-pulse rounded bg-slate-200" />
    </div>
  );
}
