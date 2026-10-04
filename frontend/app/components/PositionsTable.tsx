"use client";

import { useAppData } from "@/providers/AppDataProvider";

function formatUsd(value: number): string {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function PositionsTable() {
  const { portfolio, prices } = useAppData();
  const positions = portfolio?.positions ?? [];

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-bg-panel">
      <div className="border-b border-border px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-400">Positions</h2>
      </div>

      <div className="flex-1 overflow-auto">
        {positions.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-neutral-500">
            No open positions
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-bg-panel text-left text-[11px] uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-3 py-1.5">Ticker</th>
                <th className="px-3 py-1.5 text-right">Qty</th>
                <th className="px-3 py-1.5 text-right">Avg Cost</th>
                <th className="px-3 py-1.5 text-right">Price</th>
                <th className="px-3 py-1.5 text-right">P&amp;L</th>
                <th className="px-3 py-1.5 text-right">%</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => {
                // Live price from the SSE feed takes priority for responsiveness;
                // falls back to the value from the last /api/portfolio fetch.
                const livePrice = prices[position.ticker]?.price ?? position.current_price;
                const marketValue = livePrice != null ? position.quantity * livePrice : position.market_value;
                const costBasis = position.quantity * position.avg_cost;
                const pnl = livePrice != null ? marketValue - costBasis : position.unrealized_pnl;
                const pnlPercent = costBasis ? (pnl / costBasis) * 100 : 0;
                const pnlColor = pnl >= 0 ? "text-up" : "text-down";

                return (
                  <tr
                    key={position.ticker}
                    data-testid="position-row"
                    data-ticker={position.ticker}
                    className="border-b border-border/60"
                  >
                    <td className="px-3 py-1.5 font-mono font-semibold">{position.ticker}</td>
                    <td data-testid="position-qty" className="px-3 py-1.5 text-right font-mono tabular-nums">
                      {position.quantity}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono tabular-nums">
                      ${position.avg_cost.toFixed(2)}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono tabular-nums">
                      {livePrice != null ? `$${livePrice.toFixed(2)}` : "—"}
                    </td>
                    <td className={`px-3 py-1.5 text-right font-mono tabular-nums ${pnlColor}`}>
                      {formatUsd(pnl)}
                    </td>
                    <td className={`px-3 py-1.5 text-right font-mono tabular-nums ${pnlColor}`}>
                      {pnlPercent >= 0 ? "+" : ""}
                      {pnlPercent.toFixed(2)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
