import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = { title: "Today · Market Sentinel", description: "Evidence-first equity research." };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-rule">
          <div className="mx-auto max-w-3xl px-4 py-3 sm:px-6">
            <p className="text-sm font-semibold tracking-tight">Market Sentinel</p>
          </div>
        </header>
        {children}
        <footer className="mx-auto max-w-3xl px-4 pb-10 pt-6 text-sm text-muted sm:px-6">
          <p>Research and paper decisions only. No live orders.</p>
        </footer>
      </body>
    </html>
  );
}
