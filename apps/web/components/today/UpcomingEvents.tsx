import type { UpcomingEvent } from "../../lib/today/types";
import { Timestamp, type Zones } from "./IssueCard";

export function UpcomingEvents({ events, zones }: { events: UpcomingEvent[]; zones: Zones }) {
  return (
    <section aria-labelledby="upcoming-heading" className="mt-10">
      <h2 id="upcoming-heading" className="text-xl font-semibold">Upcoming events</h2>
      {events.length === 0 ? (
        <p className="mt-3 text-muted">No scheduled events found for your holdings within current coverage.</p>
      ) : (
        <ul className="mt-3 divide-y divide-rule border-y border-rule">
          {events.map((e) => (
            <li key={e.id} className="py-3">
              <p><span className="font-semibold">{e.holding.symbol}</span> {e.title}</p>
              <p className="text-sm text-muted"><Timestamp utc={e.at} zones={zones} /></p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
