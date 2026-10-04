"use client";

import { useState } from "react";
import { executeTrade, TradeApiError } from "@/lib/api";
import { useAppData } from "@/providers/AppDataProvider";
import type { TradeSide } from "@/types";

export function TradeBar() {
  const { selectedTicker, refreshPortfolio, refreshTrades, refreshSnapshots } = useAppData();
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveTicker = (ticker || selectedTicker || "").trim().toUpperCase();

  async function submit(side: TradeSide) {
    const qty = Number(quantity);
    if (!effectiveTicker || !qty || qty <= 0 || pending) return;

    setPending(true);
    setError(null);
    try {
      await executeTrade(effectiveTicker, qty, side);
      setQuantity("");
      await Promise.all([refreshPortfolio(), refreshTrades(), refreshSnapshots()]);
    } catch (err) {
      setError(err instanceof TradeApiError ? err.message : "Trade failed. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-bg-panel p-3">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">Trade</h2>
      <div className="flex items-center gap-2">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder={selectedTicker ?? "Ticker"}
          data-testid="trade-ticker-input"
          className="w-24 rounded border border-border bg-bg-raised px-2 py-1.5 text-sm uppercase text-neutral-100 outline-none focus:border-accent-blue"
        />
        <input
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="Qty"
          type="number"
          min="0"
          step="any"
          data-testid="trade-qty-input"
          className="w-24 rounded border border-border bg-bg-raised px-2 py-1.5 text-sm text-neutral-100 outline-none focus:border-accent-blue"
        />
        <button
          onClick={() => submit("buy")}
          disabled={pending}
          className="rounded bg-up px-4 py-1.5 text-sm font-semibold text-black disabled:opacity-50"
        >
          Buy
        </button>
        <button
          onClick={() => submit("sell")}
          disabled={pending}
          className="rounded bg-down px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          Sell
        </button>
      </div>
      {error && (
        <p data-testid="trade-error" className="mt-2 text-xs text-down">
          {error}
        </p>
      )}
    </div>
  );
}
