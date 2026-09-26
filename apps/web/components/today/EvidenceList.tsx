import type { EvidenceItem } from "../../lib/today/types";
import { Timestamp, type Zones } from "./IssueCard";

export function EvidenceList({ symbol, items, zones }: { symbol: string; items: EvidenceItem[]; zones: Zones }) {
  return (
    <details className="group mt-4 border-t border-rule pt-3">
      <summary className="font-medium text-accent">
        Evidence for {symbol} ({items.length} {items.length === 1 ? "source" : "sources"})
      </summary>
      <ul className="mt-3 space-y-4">
        {items.map((e) => (
          <li key={e.id} className="text-sm">
            <p className="font-medium">{e.source}</p>
            <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-3 text-muted">
              <dt>Published</dt>
              <dd><Timestamp utc={e.published_at} zones={zones} /></dd>
              <dt>Known to us</dt>
              <dd><Timestamp utc={e.known_at} zones={zones} /></dd>
            </dl>
            {e.excerpt === null ? (
              <p className="mt-2 text-muted">Excerpt not licensed for display.</p>
            ) : (
              <blockquote className="mt-2 border-l-2 border-rule pl-3">{e.excerpt}</blockquote>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
