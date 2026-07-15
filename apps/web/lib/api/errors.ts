import type { ApiValidationIssue } from "@/lib/api/types";

export type ApiErrorKind = "abort" | "http" | "network" | "parse" | "timeout";
export type ApiErrorDetail = string | ApiValidationIssue[] | undefined;

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;
  readonly requestId?: string;
  readonly detail?: ApiErrorDetail;

  constructor({
    kind,
    message,
    status,
    requestId,
    detail,
  }: {
    kind: ApiErrorKind;
    message: string;
    status?: number;
    requestId?: string;
    detail?: ApiErrorDetail;
  }) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.requestId = requestId;
    this.detail = detail;
  }
}

export class ApiTimeoutError extends ApiError {
  constructor(message = "The request timed out.") {
    super({ kind: "timeout", message });
    this.name = "ApiTimeoutError";
  }
}

export class ApiAbortError extends ApiError {
  constructor(message = "The request was cancelled.") {
    super({ kind: "abort", message });
    this.name = "ApiAbortError";
  }
}

export function validationMessage(detail: ApiErrorDetail) {
  if (typeof detail === "string") return detail;
  return detail?.map((issue) => `${issue.loc?.join(".") ?? "value"}: ${issue.msg}`).join("; ");
}

export function technicalErrorMessage(error: unknown) {
  if (!(error instanceof ApiError)) return "Unexpected client error.";
  const requestId = error.requestId ? ` Request ID: ${error.requestId}.` : "";
  return `${error.kind}${error.status ? ` (${error.status})` : ""}.${requestId}`;
}
