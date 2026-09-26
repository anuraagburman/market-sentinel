import type { ReactNode } from "react";
import type { TodayResult } from "../../lib/today/load";
import { IssueCard } from "./IssueCard";
import { LastGoodSnapshot } from "./LastGoodSnapshot";
import { RetryLink, StatusNotice } from "./StatusNotice";
import { TodayHeader } from "./TodayHeader";
import { UpcomingEvents } from "./UpcomingEvents";

interface Props { result: TodayResult; switcher?: ReactNode; retryHref?: string }

export function TodayPage({ result, switcher, retryHref = "/" }: Props) {
  if (!result.ok) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        {switcher}
        <h1 className="text-3xl font-semibold tracking-tight">Today couldn&apos;t load</h1>
        <p className="mt-4">The brief data couldn&apos;t be read, so nothing is shown here.</p>
        <p className="mt-4"><RetryLink href={retryHref} /></p>
      </main>
    );
  }
  const { view } = result;
  const zones = { exchange: view.header.exchange_timezone, user: view.header.user_timezone };
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      {switcher}
      <TodayHeader header={view.header} status={view.status} />
      <StatusNotice view={view} retryHref={retryHref} />
      {view.issues.length > 0 && (
        <section aria-labelledby="changes-heading" className="mt-8">
          <h2 id="changes-heading" className="text-xl font-semibold">Material changes</h2>
          <ol className="mt-4 space-y-4">
            {view.issues.map((issue) => (
              <li key={issue.id}><IssueCard issue={issue} zones={zones} /></li>
            ))}
          </ol>
        </section>
      )}
      {view.status !== "failed" && <UpcomingEvents events={view.upcoming_events} zones={zones} />}
      {view.last_good_snapshot && <LastGoodSnapshot snapshot={view.last_good_snapshot} zones={zones} />}
    </main>
  );
}
