"use client";

import { Line, LineChart } from "recharts";
import type { PriceHistoryPoint } from "@/hooks/useLivePrices";

interface SparklineProps {
  data: PriceHistoryPoint[];
  direction: "up" | "down" | "flat";
  width?: number;
  height?: number;
}

const COLOR = {
  up: "#2ecc71",
  down: "#e5484d",
  flat: "#6b7280",
};

export function Sparkline({ data, direction, width = 88, height = 28 }: SparklineProps) {
  if (data.length < 2) {
    return <div style={{ width, height }} className="text-center text-xs text-neutral-600" />;
  }

  return (
    <LineChart width={width} height={height} data={data}>
      <Line
        type="monotone"
        dataKey="price"
        stroke={COLOR[direction]}
        strokeWidth={1.5}
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  );
}
