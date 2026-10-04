"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAppData } from "@/providers/AppDataProvider";

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleTimeString("en-US", { hour12: false });
}

export function MainChart() {
  const { selectedTicker, history, prices } = useAppData();
  const data = selectedTicker ? history[selectedTicker] ?? [] : [];
  const latest = selectedTicker ? prices[selectedTicker] : undefined;

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-bg-panel p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-mono text-lg font-semibold text-neutral-100">
          {selectedTicker ?? "Select a ticker"}
        </h2>
        {latest && (
          <span className={`font-mono text-sm ${latest.direction === "down" ? "text-down" : "text-up"}`}>
            ${latest.price.toFixed(2)} ({latest.change_percent >= 0 ? "+" : ""}
            {latest.change_percent.toFixed(2)}%)
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1">
        {data.length < 2 ? (
          <div className="flex h-full items-center justify-center text-sm text-neutral-500">
            Waiting for live price data…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTime}
                stroke="#4b5263"
                tick={{ fontSize: 11 }}
                minTickGap={40}
              />
              <YAxis
                domain={["auto", "auto"]}
                stroke="#4b5263"
                tick={{ fontSize: 11 }}
                width={60}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
              />
              <Tooltip
                contentStyle={{ background: "#1a1a2e", border: "1px solid #2a2d3a" }}
                labelFormatter={(v: number) => formatTime(v)}
                formatter={(value: number) => [`$${value.toFixed(2)}`, "Price"]}
              />
              <Line type="monotone" dataKey="price" stroke="#209dd7" strokeWidth={1.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
