export type Direction = "up" | "down" | "flat";

export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: Direction;
}

export interface WatchlistEntry {
  ticker: string;
  added_at: string;
  price: PriceUpdate | null;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number | null;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
}

export interface Portfolio {
  cash_balance: number;
  positions: Position[];
  total_value: number;
}

export type TradeSide = "buy" | "sell";

export interface Trade {
  id?: string;
  ticker: string;
  side: TradeSide;
  quantity: number;
  price: number;
  executed_at: string;
}

export interface SnapshotPoint {
  total_value: number;
  recorded_at: string;
}

export type TradeErrorCode =
  | "insufficient_cash"
  | "insufficient_shares"
  | "no_price_available"
  | "invalid_quantity";

export interface TradeErrorResponse {
  error: TradeErrorCode;
  message: string;
}

export type ChatRole = "user" | "assistant";

export interface ChatAction {
  type: "trade" | "watchlist_change";
  detail: string;
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  actions?: ChatAction[];
}

export interface ChatResponse {
  message: string;
  trades?: Array<{ ticker: string; side: TradeSide; quantity: number; error?: string }>;
  watchlist_changes?: Array<{ ticker: string; action: "add" | "remove" }>;
}
