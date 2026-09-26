import Link from "next/link";
import { exchangeTime, localTime } from "../../lib/today/format";
import type { Issue } from "../../lib/today/types";
import { EvidenceList } from "./EvidenceList";
import { EvidenceStatusLabel, KindLabel } from "./Labels";

export interface Zones { exchange: string; user: string }

export function Timestamp({ utc, zones }: { utc: string; zones: Zones }) {
  return (
    <time dateTime={utc}>
      {exchangeTime(utc, zones.exchange)} ({localTime(utc, zones.user)} your time)
    </time>
  );
}

export function IssueCard({ issue, zones }: { issue: Issue; zones: Zones }) {
  const { holding, observation, exposure } = issue;
  const headingId = `${issue.id}-heading`;
  return (
    <article aria-labelledby={headingId} className="rounded border border-rule bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id={headingId} className="text-lg font-semibold">
          {holding.symbol} <span className="font-normal text-muted">· {holding.name}</span>
        </h3>
        <EvidenceStatusLabel status={issue.evidence_status} />
      </div>

      <div className="mt-3 space-y-3">
        <div>
          <p><KindLabel kind="fact" />{observation.text}</p>
          <p className="mt-1 text-sm text-muted">
            {observation.source} · <Timestamp utc={observation.observed_at} zones={zones} />
          </p>
        </div>

        <div>
          {exposure.kind === "calculation" ? (
            <>
              <p><KindLabel kind="calculation" />Your position is <span className="font-mono">{exposure.value}</span>.</p>
              <p className="mt-1 text-sm text-muted">{exposure.basis}</p>
            </>
          ) : (
            <>
              <p><KindLabel kind="calculation" />Exposure unavailable.</p>
              <p className="mt-1 text-sm text-muted">{exposure.reason}</p>
            </>
          )}
        </div>

        <p className="border-l-2 border-dashed border-rule pl-3 italic">
          <KindLabel kind="interpretation" />{issue.interpretation}
        </p>

        <div>
          <p className="text-sm font-medium">Next research question</p>
          <p>{issue.next_question}</p>
        </div>
      </div>

      <EvidenceList symbol={holding.symbol} items={issue.evidence} zones={zones} />

      <p className="mt-4">
        <Link href={`/investigate?issue=${encodeURIComponent(issue.id)}`} className="font-medium text-accent underline underline-offset-2">
          Investigate {holding.symbol}
        </Link>
      </p>
    </article>
  );
}
