"use client";

import { useAppData } from "@/providers/AppDataProvider";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", { hour12: false });
}

export function TradeBlotter() {
  const { trades } = useAppData();

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-bg-panel">
      <div className="border-b border-border px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-400">Trade Blotter</h2>
      </div>
      <div className="flex-1 overflow-auto">
        {trades.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-neutral-500">
            No trades yet
          </div>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {trades.map((trade, i) => (
                <tr key={trade.id ?? i} className="border-b border-border/60">
                  <td className="px-3 py-1.5 font-mono font-semibold">{trade.ticker}</td>
                  <td
                    className={`px-3 py-1.5 font-mono uppercase ${
                      trade.side === "buy" ? "text-up" : "text-down"
                    }`}
                  >
                    {trade.side}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono tabular-nums">{trade.quantity}</td>
                  <td className="px-3 py-1.5 text-right font-mono tabular-nums">
                    ${trade.price.toFixed(2)}
                  </td>
                  <td className="px-3 py-1.5 text-right text-xs text-neutral-500">
                    {formatTime(trade.executed_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
