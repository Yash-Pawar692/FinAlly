"use client";

import { ResponsiveContainer, Treemap } from "recharts";
import { useAppData } from "@/providers/AppDataProvider";

interface CellDatum {
  name: string;
  size: number;
  pnlPercent: number;
}

interface TreemapContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPercent?: number;
}

function colorForPnl(pnlPercent: number): string {
  const intensity = Math.min(Math.abs(pnlPercent) / 10, 1);
  if (pnlPercent > 0) return `rgba(46, 204, 113, ${0.25 + intensity * 0.6})`;
  if (pnlPercent < 0) return `rgba(229, 72, 77, ${0.25 + intensity * 0.6})`;
  return "rgba(107, 114, 128, 0.4)";
}

function CellContent({ x = 0, y = 0, width = 0, height = 0, name = "", pnlPercent = 0 }: TreemapContentProps) {
  if (width < 2 || height < 2) return null;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={colorForPnl(pnlPercent)} stroke="#0d1117" />
      {width > 40 && height > 24 && (
        <text
          x={x + width / 2}
          y={y + height / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#e6e8ef"
          fontSize={12}
          fontFamily="monospace"
        >
          {name}
        </text>
      )}
      {width > 40 && height > 40 && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 16}
          textAnchor="middle"
          fill="#9ca3af"
          fontSize={10}
          fontFamily="monospace"
        >
          {pnlPercent >= 0 ? "+" : ""}
          {pnlPercent.toFixed(1)}%
        </text>
      )}
    </g>
  );
}

export function Heatmap() {
  const { portfolio, prices } = useAppData();
  const positions = portfolio?.positions ?? [];

  const data: CellDatum[] = positions.map((position) => {
    const livePrice = prices[position.ticker]?.price ?? position.current_price ?? position.avg_cost;
    const marketValue = position.quantity * livePrice;
    const costBasis = position.quantity * position.avg_cost;
    const pnlPercent = costBasis ? ((marketValue - costBasis) / costBasis) * 100 : 0;
    return { name: position.ticker, size: Math.max(marketValue, 1), pnlPercent };
  });

  return (
    <div data-testid="heatmap" className="flex h-full flex-col rounded-lg border border-border bg-bg-panel p-3">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">
        Portfolio Heatmap
      </h2>
      <div className="min-h-0 flex-1">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-neutral-500">
            No positions to display
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              stroke="#0d1117"
              content={<CellContent />}
              isAnimationActive={false}
            />
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
