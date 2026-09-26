import type { ReactNode } from "react";
import type { TodayResult } from "../../lib/today/load";
import { IssueCard } from "./IssueCard";
import { TodayHeader } from "./TodayHeader";
import { UpcomingEvents } from "./UpcomingEvents";

export function TodayPage({ result, switcher }: { result: TodayResult; switcher?: ReactNode }) {
  if (!result.ok) return <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">{switcher}</main>;
  const { view } = result;
  const zones = { exchange: view.header.exchange_timezone, user: view.header.user_timezone };
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      {switcher}
      <TodayHeader header={view.header} />
      <section aria-labelledby="changes-heading" className="mt-8">
        <h2 id="changes-heading" className="text-xl font-semibold">Material changes</h2>
        <ol className="mt-4 space-y-4">
          {view.issues.map((issue) => (
            <li key={issue.id}><IssueCard issue={issue} zones={zones} /></li>
          ))}
        </ol>
      </section>
      <UpcomingEvents events={view.upcoming_events} zones={zones} />
    </main>
  );
}
