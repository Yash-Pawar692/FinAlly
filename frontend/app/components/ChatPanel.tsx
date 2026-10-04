"use client";

import { useRef, useState } from "react";
import { sendChatMessage } from "@/lib/api";
import { useAppData } from "@/providers/AppDataProvider";
import type { ChatAction, ChatMessage } from "@/types";

let nextId = 0;
function newId(): string {
  nextId += 1;
  return `msg-${nextId}`;
}

export function ChatPanel() {
  const { refreshPortfolio, refreshTrades, refreshSnapshots, refreshWatchlist } = useAppData();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { id: newId(), role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendChatMessage(text);

      const actions: ChatAction[] = [
        ...(response.trades ?? []).map((t) => ({
          type: "trade" as const,
          detail: `${t.side.toUpperCase()} ${t.quantity} ${t.ticker}`,
          error: t.error,
        })),
        ...(response.watchlist_changes ?? []).map((w) => ({
          type: "watchlist_change" as const,
          detail: `${w.action === "add" ? "Added" : "Removed"} ${w.ticker}`,
        })),
      ];

      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "assistant", content: response.message, actions },
      ]);

      if (actions.length > 0) {
        await Promise.all([refreshPortfolio(), refreshTrades(), refreshSnapshots(), refreshWatchlist()]);
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "assistant", content: "Sorry, something went wrong reaching the assistant." },
      ]);
    } finally {
      setLoading(false);
      requestAnimationFrame(() => {
        listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
      });
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-bg-panel">
      <div className="border-b border-border px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-400">AI Copilot</h2>
      </div>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-3">
        {messages.length === 0 && (
          <p className="text-sm text-neutral-500">
            Ask FinAlly about your portfolio, request analysis, or tell it to trade for you.
          </p>
        )}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${
              message.role === "user"
                ? "ml-auto bg-accent-blue text-white"
                : "bg-bg-raised text-neutral-100"
            }`}
          >
            <p className="whitespace-pre-wrap">{message.content}</p>
            {message.actions && message.actions.length > 0 && (
              <ul className="mt-2 space-y-1 border-t border-white/10 pt-2 text-xs">
                {message.actions.map((action, i) => (
                  <li key={i} className={action.error ? "text-down" : "text-up"}>
                    {action.error ? `✗ ${action.detail} — ${action.error}` : `✓ ${action.detail}`}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {loading && <p className="text-sm text-neutral-500">FinAlly is thinking…</p>}
      </div>

      <div className="flex items-center gap-2 border-t border-border p-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask FinAlly…"
          className="w-full rounded border border-border bg-bg-raised px-2 py-1.5 text-sm text-neutral-100 outline-none focus:border-accent-purple"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="shrink-0 rounded bg-accent-purple px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
