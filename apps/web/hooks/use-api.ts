"use client";

import { useCallback, useState } from "react";

export function useApi<T, Args extends unknown[]>(request: (...args: Args) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(false);

  const execute = useCallback(
    async (...args: Args) => {
      setLoading(true);
      setError(null);
      try {
        const result = await request(...args);
        setData(result);
        return result;
      } catch (caught) {
        const requestError = caught instanceof Error ? caught : new Error("Request failed.");
        setError(requestError);
        throw requestError;
      } finally {
        setLoading(false);
      }
    },
    [request],
  );

  return { data, error, execute, loading };
}
