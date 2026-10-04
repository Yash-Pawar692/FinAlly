"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useLivePrices, type ConnectionStatus, type PriceHistoryPoint } from "@/hooks/useLivePrices";
import { getPortfolio, getPortfolioHistory, getTrades, getWatchlist } from "@/lib/api";
import type { Portfolio, PriceUpdate, SnapshotPoint, Trade, WatchlistEntry } from "@/types";

interface AppDataContextValue {
  prices: Record<string, PriceUpdate>;
  history: Record<string, PriceHistoryPoint[]>;
  connectionStatus: ConnectionStatus;
  portfolio: Portfolio | null;
  refreshPortfolio: () => Promise<void>;
  watchlist: WatchlistEntry[];
  refreshWatchlist: () => Promise<void>;
  snapshots: SnapshotPoint[];
  refreshSnapshots: () => Promise<void>;
  trades: Trade[];
  refreshTrades: () => Promise<void>;
  selectedTicker: string | null;
  setSelectedTicker: (ticker: string) => void;
}

const AppDataContext = createContext<AppDataContextValue | null>(null);

const PORTFOLIO_POLL_MS = 5000;
const SNAPSHOT_POLL_MS = 30000;

export function AppDataProvider({ children }: { children: ReactNode }) {
  const { prices, history, status } = useLivePrices();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [snapshots, setSnapshots] = useState<SnapshotPoint[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const refreshPortfolio = useCallback(async () => {
    try {
      setPortfolio(await getPortfolio());
    } catch (err) {
      console.error("Failed to refresh portfolio", err);
    }
  }, []);

  const refreshWatchlist = useCallback(async () => {
    try {
      const list = await getWatchlist();
      setWatchlist(list);
      setSelectedTicker((current) => current ?? list[0]?.ticker ?? null);
    } catch (err) {
      console.error("Failed to refresh watchlist", err);
    }
  }, []);

  const refreshSnapshots = useCallback(async () => {
    try {
      setSnapshots(await getPortfolioHistory());
    } catch (err) {
      console.error("Failed to refresh portfolio history", err);
    }
  }, []);

  const refreshTrades = useCallback(async () => {
    try {
      setTrades(await getTrades());
    } catch (err) {
      console.error("Failed to refresh trade history", err);
    }
  }, []);

  useEffect(() => {
    refreshPortfolio();
    refreshWatchlist();
    refreshSnapshots();
    refreshTrades();

    const portfolioInterval = setInterval(refreshPortfolio, PORTFOLIO_POLL_MS);
    const snapshotInterval = setInterval(refreshSnapshots, SNAPSHOT_POLL_MS);
    return () => {
      clearInterval(portfolioInterval);
      clearInterval(snapshotInterval);
    };
  }, [refreshPortfolio, refreshWatchlist, refreshSnapshots, refreshTrades]);

  return (
    <AppDataContext.Provider
      value={{
        prices,
        history,
        connectionStatus: status,
        portfolio,
        refreshPortfolio,
        watchlist,
        refreshWatchlist,
        snapshots,
        refreshSnapshots,
        trades,
        refreshTrades,
        selectedTicker,
        setSelectedTicker,
      }}
    >
      {children}
    </AppDataContext.Provider>
  );
}

export function useAppData(): AppDataContextValue {
  const ctx = useContext(AppDataContext);
  if (!ctx) {
    throw new Error("useAppData must be used within AppDataProvider");
  }
  return ctx;
}
