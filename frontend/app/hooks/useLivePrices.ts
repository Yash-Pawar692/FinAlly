"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";
import type { PriceUpdate } from "@/types";

export type ConnectionStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface PriceHistoryPoint {
  timestamp: number;
  price: number;
}

// Sparklines and the main chart are built entirely client-side from the SSE
// stream since page load — there is no server-side per-ticker history
// (PLAN.md §10). Capped so memory doesn't grow unbounded on a long session.
const MAX_HISTORY_POINTS = 300;

export function useLivePrices() {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [history, setHistory] = useState<Record<string, PriceHistoryPoint[]>>({});
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/api/stream/prices`);
    sourceRef.current = source;

    source.onopen = () => setStatus("connected");

    source.onmessage = (event) => {
      setStatus("connected");
      const data: Record<string, PriceUpdate> = JSON.parse(event.data);

      setPrices((prev) => ({ ...prev, ...data }));
      setHistory((prev) => {
        const next = { ...prev };
        for (const [ticker, update] of Object.entries(data)) {
          const existing = next[ticker] ?? [];
          next[ticker] = [...existing, { timestamp: update.timestamp, price: update.price }].slice(
            -MAX_HISTORY_POINTS
          );
        }
        return next;
      });
    };

    // EventSource retries automatically; readyState tells us whether it's
    // still trying (CONNECTING) or has given up (CLOSED) so the header's
    // connection dot (PLAN.md §2, §10) reflects reality.
    source.onerror = () => {
      setStatus(source.readyState === EventSource.CONNECTING ? "reconnecting" : "disconnected");
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, []);

  return { prices, history, status };
}
