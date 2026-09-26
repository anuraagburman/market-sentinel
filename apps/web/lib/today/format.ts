import type { SessionName } from "./types";

// ICU puts a narrow no-break space before AM/PM; plain spaces keep copy searchable and stable.
const clean = (s: string) => s.replace(/[  ]/g, " ");

function format(utc: string, timeZone: string, options: Intl.DateTimeFormatOptions) {
  return clean(new Intl.DateTimeFormat("en-US", { timeZone, ...options }).format(new Date(utc)));
}

/** "Mon, Sep 28, 7:30 AM EDT" */
export function exchangeTime(utc: string, timeZone: string) {
  return format(utc, timeZone, {
    weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short",
  });
}

/** "Mon, 4:30 AM PDT" — the weekday stays so a date change across zones is visible. */
export function localTime(utc: string, timeZone: string) {
  return format(utc, timeZone, { weekday: "short", hour: "numeric", minute: "2-digit", timeZoneName: "short" });
}

/** A calendar date ("2026-09-28") as "Monday, September 28, 2026". */
export function sessionDate(date: string) {
  return format(`${date}T12:00:00Z`, "UTC", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}

export const SESSION_LABELS: Record<SessionName, string> = {
  pre_market: "Pre-market",
  regular: "Regular session",
  after_hours: "After hours",
  closed: "Market closed",
};
