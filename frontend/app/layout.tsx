import type { Metadata } from "next";
import "./globals.css";
import { AppDataProvider } from "@/providers/AppDataProvider";

export const metadata: Metadata = {
  title: "FinAlly — AI Trading Workstation",
  description: "A simulated AI-powered trading terminal with a live market feed and chat copilot.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg-base font-sans antialiased">
        <AppDataProvider>{children}</AppDataProvider>
      </body>
    </html>
  );
}
