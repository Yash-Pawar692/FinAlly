"use client";

import { useAppData } from "@/providers/AppDataProvider";
import type { ConnectionStatus } from "@/hooks/useLivePrices";

const STATUS_COLOR: Record<ConnectionStatus, string> = {
  connected: "bg-up",
  connecting: "bg-accent-yellow",
  reconnecting: "bg-accent-yellow",
  disconnected: "bg-down",
};

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  connected: "Connected",
  connecting: "Connecting",
  reconnecting: "Reconnecting",
  disconnected: "Disconnected",
};

function formatUsd(value: number): string {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function Header() {
  const { portfolio, connectionStatus } = useAppData();

  return (
    <header className="flex items-center justify-between border-b border-border bg-bg-panel px-5 py-3">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold tracking-tight text-accent-yellow">FinAlly</span>
        <span className="text-xs text-neutral-500">AI Trading Workstation</span>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full ${STATUS_COLOR[connectionStatus]}`}
            title={STATUS_LABEL[connectionStatus]}
          />
          <span data-testid="connection-status" className="text-neutral-400">
            {STATUS_LABEL[connectionStatus]}
          </span>
        </div>

        <div className="flex flex-col items-end">
          <span className="text-[11px] uppercase tracking-wide text-neutral-500">Cash</span>
          <span data-testid="cash-balance" className="font-mono text-neutral-200">
            {portfolio ? formatUsd(portfolio.cash_balance) : "—"}
          </span>
        </div>

        <div className="flex flex-col items-end">
          <span className="text-[11px] uppercase tracking-wide text-neutral-500">Total Value</span>
          <span className="font-mono text-base font-semibold text-accent-blue">
            {portfolio ? formatUsd(portfolio.total_value) : "—"}
          </span>
        </div>
      </div>
    </header>
  );
}
