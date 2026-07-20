import { vi } from "vitest";

type Route = (request: Request) => Response | Promise<Response>;

export function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Dependency-free equivalent to MSW for API-client and browser request tests. */
export function createMockServer(routes: Record<string, Route>) {
  const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    const route = routes[`${request.method} ${new URL(request.url).pathname}`];
    return route
      ? route(request)
      : json({ detail: `Unhandled ${request.method} ${new URL(request.url).pathname}` }, 500);
  });
  return { fetch, reset: () => fetch.mockClear() };
}
