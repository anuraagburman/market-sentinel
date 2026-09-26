import type { ReactNode } from "react";
import type { TodayResult } from "../../lib/today/load";
import { TodayHeader } from "./TodayHeader";

export function TodayPage({ result, switcher }: { result: TodayResult; switcher?: ReactNode }) {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      {switcher}
      {result.ok && <TodayHeader header={result.view.header} />}
    </main>
  );
}
