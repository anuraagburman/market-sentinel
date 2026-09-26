import type { ReactNode } from "react";
import type { TodayView } from "../../lib/today/types";
import { Timestamp } from "./IssueCard";
import { WarningIcon } from "./Labels";

const labels = (items: { label: string }[]) => items.map((s) => s.label).join(", ");

function Notice({ title, children, warn = false }: { title: string; children: ReactNode; warn?: boolean }) {
  return (
    <div role="status" className={`mt-6 rounded border p-4 ${warn ? "border-warn-rule bg-warn-soft text-warn" : "border-rule bg-surface"}`}>
      <p className="flex items-center gap-2 font-semibold">{warn && <WarningIcon />}{title}</p>
      <div className="mt-1 space-y-2">{children}</div>
    </div>
  );
}

export function RetryLink({ href }: { href: string }) {
  return <a href={href} className="inline-block font-medium text-accent underline underline-offset-2">Retry</a>;
}

/** What was checked and what's missing, for every state that isn't a clean ready brief. */
export function StatusNotice({ view, retryHref }: { view: TodayView; retryHref: string }) {
  const { checked, failed, pending = [] } = view.header.coverage;
  const zones = { exchange: view.header.exchange_timezone, user: view.header.user_timezone };
  switch (view.status) {
    case "running":
      return (
        <Notice title="Brief in progress">
          <p>
            Checked so far: {checked.length > 0 ? labels(checked) : "none"}. Still checking: {labels(pending)}.
            Results appear once every source has been checked.
          </p>
        </Notice>
      );
    case "stale":
      return (
        <Notice title="This brief is out of date" warn>
          <p>
            The newest complete data is from <Timestamp utc={view.header.snapshot_at} zones={zones} />.
            Today&apos;s refresh hasn&apos;t produced newer results, so nothing here is current.
          </p>
          <RetryLink href={retryHref} />
        </Notice>
      );
    case "partial":
      return (
        <Notice title="Partial brief" warn>
          <p>
            {labels(failed)} couldn&apos;t be checked. The issues below come from {labels(checked)} only;
            changes reported only by {labels(failed)} may be missing.
          </p>
        </Notice>
      );
    case "failed":
      return (
        <Notice title="This morning's brief didn't complete" warn>
          <p>
            {checked.length === 0 ? "No sources could be checked." : `Only ${labels(checked)} could be checked.`}{" "}
            Failed: {labels(failed)}. There are no current results to show.
          </p>
          <RetryLink href={retryHref} />
        </Notice>
      );
    case "no_material_change":
      // Empty coverage or a failed source is never a clean day, whatever the status says.
      if (checked.length === 0 || failed.length > 0) {
        return (
          <Notice title="Coverage incomplete" warn>
            <p>
              {checked.length === 0 ? "No sources were checked" : `${labels(failed)} couldn't be checked`}, so Today
              can&apos;t say whether anything changed.
            </p>
            <RetryLink href={retryHref} />
          </Notice>
        );
      }
      return (
        <Notice title="No new material changes found within current coverage.">
          <details>
            <summary className="font-medium text-accent">View monitored coverage</summary>
            <ul className="mt-2 list-disc pl-5">
              {checked.map((s) => <li key={s.id}>{s.label}: checked</li>)}
              {view.header.coverage.unpriced.map((h) => (
                <li key={h.instrument_id}>{h.symbol} ({h.name}): price unavailable</li>
              ))}
            </ul>
          </details>
        </Notice>
      );
    default:
      return null;
  }
}
