"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAppData } from "@/providers/AppDataProvider";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour12: false });
}

export function PnlChart() {
  const { snapshots } = useAppData();

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-bg-panel p-3">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">
        Portfolio Value
      </h2>
      <div className="min-h-0 flex-1">
        {snapshots.length < 2 ? (
          <div className="flex h-full items-center justify-center text-sm text-neutral-500">
            Accumulating history…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={snapshots}>
              <XAxis
                dataKey="recorded_at"
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
                labelFormatter={(v: string) => formatTime(v)}
                formatter={(value: number) => [`$${value.toFixed(2)}`, "Total Value"]}
              />
              <Line
                type="monotone"
                dataKey="total_value"
                stroke="#ecad0a"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
