"use client";

import { useState } from "react";
import { addWatchlistTicker, removeWatchlistTicker } from "@/lib/api";
import { useAppData } from "@/providers/AppDataProvider";
import { WatchlistRow } from "./WatchlistRow";

export function WatchlistPanel() {
  const { watchlist, prices, history, selectedTicker, setSelectedTicker, refreshWatchlist } = useAppData();
  const [newTicker, setNewTicker] = useState("");
  const [pending, setPending] = useState(false);

  async function handleAdd() {
    const ticker = newTicker.trim().toUpperCase();
    if (!ticker || pending) return;
    setPending(true);
    try {
      await addWatchlistTicker(ticker);
      setNewTicker("");
      await refreshWatchlist();
    } catch (err) {
      console.error(err);
    } finally {
      setPending(false);
    }
  }

  async function handleRemove(ticker: string) {
    try {
      await removeWatchlistTicker(ticker);
      await refreshWatchlist();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-bg-panel">
      <div className="border-b border-border px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-400">Watchlist</h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {watchlist.map((entry) => (
          <WatchlistRow
            key={entry.ticker}
            ticker={entry.ticker}
            price={prices[entry.ticker] ?? entry.price}
            history={history[entry.ticker] ?? []}
            selected={entry.ticker === selectedTicker}
            onSelect={setSelectedTicker}
            onRemove={handleRemove}
          />
        ))}
      </div>

      <div className="flex items-center gap-2 border-t border-border p-2">
        <input
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Add ticker…"
          className="w-full rounded border border-border bg-bg-raised px-2 py-1 text-sm uppercase text-neutral-100 outline-none focus:border-accent-blue"
        />
        <button
          onClick={handleAdd}
          disabled={pending}
          className="shrink-0 rounded bg-accent-blue px-3 py-1 text-sm font-medium text-white disabled:opacity-50"
        >
          Add
        </button>
      </div>
    </div>
  );
}
