import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";
import { Heatmap } from "@/components/Heatmap";
import { MainChart } from "@/components/MainChart";
import { PnlChart } from "@/components/PnlChart";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { TradeBlotter } from "@/components/TradeBlotter";
import { WatchlistPanel } from "@/components/WatchlistPanel";

export default function HomePage() {
  return (
    <div className="flex h-screen flex-col">
      <Header />

      <main className="grid flex-1 grid-cols-12 gap-3 overflow-hidden p-3">
        <section className="col-span-3 flex min-h-0 flex-col gap-3">
          <div className="min-h-0 flex-1">
            <WatchlistPanel />
          </div>
          <TradeBar />
        </section>

        <section className="col-span-6 grid min-h-0 grid-rows-2 gap-3">
          <div className="min-h-0">
            <MainChart />
          </div>
          <div className="grid min-h-0 grid-cols-2 gap-3">
            <PositionsTable />
            <Heatmap />
          </div>
        </section>

        <section className="col-span-3 flex min-h-0 flex-col gap-3">
          <div className="min-h-0 flex-1">
            <ChatPanel />
          </div>
        </section>
      </main>

      <footer className="grid grid-cols-2 gap-3 border-t border-border p-3" style={{ height: "220px" }}>
        <PnlChart />
        <TradeBlotter />
      </footer>
    </div>
  );
}
