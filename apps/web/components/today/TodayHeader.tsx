import { exchangeTime, localTime, SESSION_LABELS, sessionDate } from "../../lib/today/format";
import type { SurfaceStatus, TodayHeader as Header } from "../../lib/today/types";
import { WarningIcon } from "./Labels";

const list = (items: { label: string }[]) => items.map((s) => s.label).join(", ");
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

// A run that hasn't finished, or failed, has a cutoff but no data "as of" it.
const SNAPSHOT_LABEL: Partial<Record<SurfaceStatus, string>> = {
  running: "Checking data up to",
  failed: "Attempted cutoff",
};

export function TodayHeader({ header, status }: { header: Header; status: SurfaceStatus }) {
  const { coverage } = header;
  return (
    <header className="border-b border-rule pb-5">
      <h1 className="text-3xl font-semibold tracking-tight">Today</h1>
      <p className="mt-1 text-muted">
        {SESSION_LABELS[header.session.name]} · {sessionDate(header.session.date)}
      </p>
      <dl className="mt-4 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[max-content_1fr]">
        <dt className="font-medium">{SNAPSHOT_LABEL[status] ?? "Data as of"}</dt>
        <dd>
          <time dateTime={header.snapshot_at}>{exchangeTime(header.snapshot_at, header.exchange_timezone)}</time>
          <span className="text-muted"> · {localTime(header.snapshot_at, header.user_timezone)} your time</span>
        </dd>
        <dt className="font-medium">Coverage</dt>
        <dd data-testid="coverage-line">
          {coverage.checked.length > 0
            ? `${plural(coverage.checked.length, "source", "sources")} checked: ${list(coverage.checked)}.`
            : "No sources checked."}
          {coverage.failed.length > 0 && (
            <span className="text-warn">
              {" "}<WarningIcon /> {plural(coverage.failed.length, "source", "sources")} failed: {list(coverage.failed)}.
            </span>
          )}
          {coverage.unpriced.length > 0 && (
            <span>
              {" "}Price unavailable for {coverage.unpriced.map((h) => h.symbol).join(", ")}.
            </span>
          )}
        </dd>
      </dl>
    </header>
  );
}
