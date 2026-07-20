"use client";

import { useEffect, useRef, useState } from "react";
import type { Plan } from "@/lib/api/types";

type StreamState = "idle" | "connecting" | "streaming" | "done" | "error";

/**
 * Subscribes to the /api/v1/plans/{planId}/stream SSE endpoint and returns
 * the latest plan snapshot. Automatically reconnects on error up to maxRetries.
 *
 * Falls back gracefully when EventSource is unavailable (server-side render).
 */
export function usePlanStream(planId: string | null | undefined) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [state, setState] = useState<StreamState>("idle");
  const esRef = useRef<EventSource | null>(null);
  const retriesRef = useRef(0);
  const maxRetries = 3;

  useEffect(() => {
    if (!planId || typeof window === "undefined") return;

    function connect() {
      setState("connecting");
      // EventSource cannot attach an Authorization header. The same-origin proxy forwards
      // the HTTP-only local session cookie to the API without exposing it to browser code.
      const url = `/api/plans/${planId}/stream`;
      const es = new EventSource(url, { withCredentials: true });
      esRef.current = es;

      es.onopen = () => {
        setState("streaming");
        retriesRef.current = 0;
      };

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as Plan;
          setPlan(data);
        } catch {
          // Ignore malformed frames
        }
      };

      es.addEventListener("done", () => {
        setState("done");
        es.close();
      });

      es.onerror = () => {
        es.close();
        if (retriesRef.current < maxRetries) {
          retriesRef.current += 1;
          const delay = 1000 * 2 ** retriesRef.current;
          setTimeout(connect, delay);
        } else {
          setState("error");
        }
      };
    }

    connect();

    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, [planId]);

  return { plan, state };
}
