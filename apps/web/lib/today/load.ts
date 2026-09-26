import failed from "../../fixtures/today/failed.json";
import noMaterialChange from "../../fixtures/today/no_material_change.json";
import partial from "../../fixtures/today/partial.json";
import ready from "../../fixtures/today/ready.json";
import running from "../../fixtures/today/running.json";
import stale from "../../fixtures/today/stale.json";
import unreadable from "../../fixtures/today/unreadable.json";
import { SURFACE_STATUSES, type SurfaceStatus, type TodayView } from "./types";

export type TodayResult = { ok: true; view: TodayView } | { ok: false };

// Fixture source until the /briefs API exists. Keys are what the dev switcher can request.
const FIXTURES: Record<string, unknown> = {
  ready, running, partial, stale, failed, no_material_change: noMaterialChange, unreadable,
};

export const FIXTURE_STATES = Object.keys(FIXTURES);

export function loadToday(state: string): TodayResult {
  return parseToday(FIXTURES[state]);
}

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const isString = (v: unknown): v is string => typeof v === "string" && v.length > 0;
const isArrayOf = (v: unknown, item: (x: unknown) => boolean) => Array.isArray(v) && v.every(item);
const isSource = (v: unknown) => isObject(v) && isString(v.id) && isString(v.label);
const isHolding = (v: unknown) => isObject(v) && isString(v.instrument_id) && isString(v.symbol) && isString(v.name);

// Formatting throws RangeError on a bad date or zone, so both are checked here rather than at render.
// The round trip rejects out-of-range values like 2026-02-30 that Date would roll over.
const isCalendarDate = (v: unknown) =>
  isString(v) && /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v)) &&
  new Date(v).toISOString().slice(0, 10) === v;
const isUtcTimestamp = (v: unknown) =>
  isString(v) && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?Z$/.test(v) && isCalendarDate(v.slice(0, 10)) &&
  !Number.isNaN(Date.parse(v));
function isTimeZone(v: unknown) {
  if (!isString(v)) return false;
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: v });
    return true;
  } catch {
    return false;
  }
}

function isIssue(v: unknown) {
  if (!isObject(v) || !isString(v.id) || !isHolding(v.holding)) return false;
  const { observation: o, exposure: x } = v;
  const exposureOk =
    isObject(x) && ((x.kind === "calculation" && isString(x.value) && isString(x.basis)) ||
      (x.kind === "unavailable" && isString(x.reason)));
  return (
    isObject(o) && isString(o.text) && isString(o.source) && isUtcTimestamp(o.observed_at) &&
    isString(v.interpretation) && isString(v.next_question) && exposureOk &&
    ["supported", "partial", "contested", "insufficient"].includes(v.evidence_status as string) &&
    isArrayOf(v.evidence, (e) =>
      isObject(e) && isString(e.id) && isString(e.source) && isUtcTimestamp(e.published_at) &&
      isUtcTimestamp(e.known_at) && (e.excerpt === null || isString(e.excerpt)))
  );
}

/**
 * Shape check at the boundary. Anything that fails is "couldn't load" — a malformed brief is never
 * rendered as partial financial content.
 */
export function parseToday(raw: unknown): TodayResult {
  if (!isObject(raw) || !isObject(raw.view)) return { ok: false };
  const v = raw.view;
  const h = v.header;
  if (!isObject(h) || !isObject(h.session) || !isCalendarDate(h.session.date) || !isUtcTimestamp(h.snapshot_at)) return { ok: false };
  if (!isTimeZone(h.user_timezone) || !isTimeZone(h.exchange_timezone)) return { ok: false };
  const c = h.coverage;
  if (!isObject(c) || !isArrayOf(c.checked, isSource) || !isArrayOf(c.failed, isSource)) return { ok: false };
  if ((c.pending !== undefined && !isArrayOf(c.pending, isSource)) || !isArrayOf(c.unpriced, isHolding)) return { ok: false };
  if (!SURFACE_STATUSES.includes(v.status as SurfaceStatus)) return { ok: false };
  if (!isArrayOf(v.issues, isIssue) || (v.issues as unknown[]).length > 3) return { ok: false };
  const eventsOk = isArrayOf(v.upcoming_events, (e) =>
    isObject(e) && isString(e.id) && isHolding(e.holding) && isString(e.title) && isUtcTimestamp(e.at));
  if (!eventsOk) return { ok: false };
  const s = v.last_good_snapshot;
  if (s !== undefined && !(isObject(s) && isString(s.brief_id) && isUtcTimestamp(s.snapshot_at) && isArrayOf(s.issues, isIssue))) {
    return { ok: false };
  }
  return { ok: true, view: v as unknown as TodayView };
}
