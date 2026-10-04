"use client";

import { useFlash } from "@/hooks/useFlash";
import type { PriceHistoryPoint } from "@/hooks/useLivePrices";
import type { PriceUpdate } from "@/types";
import { Sparkline } from "./Sparkline";

interface WatchlistRowProps {
  ticker: string;
  price: PriceUpdate | null;
  history: PriceHistoryPoint[];
  selected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

const FLASH_CLASS = {
  up: "animate-flash-up",
  down: "animate-flash-down",
};

export function WatchlistRow({ ticker, price, history, selected, onSelect, onRemove }: WatchlistRowProps) {
  const { direction, flashKey } = useFlash(price?.price);
  const changeColor =
    price?.direction === "up" ? "text-up" : price?.direction === "down" ? "text-down" : "text-neutral-400";

  return (
    <div
      onClick={() => onSelect(ticker)}
      data-testid="watchlist-row"
      data-ticker={ticker}
      className={`group flex cursor-pointer items-center justify-between gap-2 border-b border-border/60 px-3 py-2 text-sm hover:bg-bg-raised ${
        selected ? "bg-bg-raised" : ""
      }`}
    >
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <span className="font-mono font-semibold text-neutral-100">{ticker}</span>
      </div>

      <Sparkline data={history} direction={price?.direction ?? "flat"} />

      <div className="flex w-20 flex-col items-end">
        <span
          key={flashKey}
          data-testid="watchlist-price"
          className={`font-mono tabular-nums ${direction ? FLASH_CLASS[direction] : ""}`}
        >
          {price ? `$${price.price.toFixed(2)}` : "—"}
        </span>
        <span className={`text-[11px] tabular-nums ${changeColor}`}>
          {price ? `${price.change_percent >= 0 ? "+" : ""}${price.change_percent.toFixed(2)}%` : ""}
        </span>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove(ticker);
        }}
        className="invisible shrink-0 px-1 text-neutral-500 hover:text-down group-hover:visible"
        aria-label={`Remove ${ticker} from watchlist`}
      >
        ×
      </button>
    </div>
  );
}
