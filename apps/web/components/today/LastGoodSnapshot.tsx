import type { LastGoodSnapshot as Snapshot } from "../../lib/today/types";
import { Timestamp, type Zones } from "./IssueCard";

/** A previous complete brief, kept visibly apart from current results and labeled with its time. */
export function LastGoodSnapshot({ snapshot, zones }: { snapshot: Snapshot; zones: Zones }) {
  return (
    <section aria-labelledby="last-good-heading" data-snapshot="previous"
      className="mt-8 rounded border border-dashed border-rule bg-canvas p-4 text-muted">
      <h2 id="last-good-heading" className="text-lg font-semibold text-ink">Last complete brief (not current)</h2>
      <p className="mt-1 text-sm">
        Data as of <Timestamp utc={snapshot.snapshot_at} zones={zones} />. Shown for reference; it may be out of date.
      </p>
      <ul className="mt-3 space-y-3">
        {snapshot.issues.map((issue) => (
          <li key={issue.id} className="text-sm">
            <p><span className="font-semibold">{issue.holding.symbol}</span> · {issue.observation.text}</p>
            <p>{issue.observation.source} · <Timestamp utc={issue.observation.observed_at} zones={zones} /></p>
          </li>
        ))}
      </ul>
    </section>
  );
}
