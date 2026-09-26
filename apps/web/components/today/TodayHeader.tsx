import { exchangeTime, localTime, SESSION_LABELS, sessionDate } from "../../lib/today/format";
import type { TodayHeader as Header } from "../../lib/today/types";

const list = (items: { label: string }[]) => items.map((s) => s.label).join(", ");
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export function TodayHeader({ header }: { header: Header }) {
  const { coverage } = header;
  return (
    <header className="border-b border-rule pb-5">
      <h1 className="text-3xl font-semibold tracking-tight">Today</h1>
      <p className="mt-1 text-muted">
        {SESSION_LABELS[header.session.name]} · {sessionDate(header.session.date)}
      </p>
      <dl className="mt-4 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[max-content_1fr]">
        <dt className="font-medium">Data as of</dt>
        <dd>
          <time dateTime={header.snapshot_at}>{exchangeTime(header.snapshot_at, header.exchange_timezone)}</time>
          <span className="text-muted"> · {localTime(header.snapshot_at, header.user_timezone)} your time</span>
        </dd>
        <dt className="font-medium">Coverage</dt>
        <dd data-testid="coverage-line">
          {coverage.checked.length > 0
            ? `${plural(coverage.checked.length, "source", "sources")} checked: ${list(coverage.checked)}.`
            : "No sources checked."}
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
