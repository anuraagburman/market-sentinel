import failed from "../../fixtures/today/failed.json";
import partial from "../../fixtures/today/partial.json";
import ready from "../../fixtures/today/ready.json";
import unreadable from "../../fixtures/today/unreadable.json";
import { SURFACE_STATUSES, type SurfaceStatus, type TodayView } from "./types";

export type TodayResult = { ok: true; view: TodayView } | { ok: false };

// Fixture source until the /briefs API exists. Keys are what the dev switcher can request.
const FIXTURES: Record<string, unknown> = { ready, partial, failed, unreadable };

export const FIXTURE_STATES = Object.keys(FIXTURES);

export function loadToday(state: string): TodayResult {
  return parseToday(FIXTURES[state]);
}

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const isString = (v: unknown): v is string => typeof v === "string" && v.length > 0;
const isArrayOf = (v: unknown, item: (x: unknown) => boolean) => Array.isArray(v) && v.every(item);
const isSource = (v: unknown) => isObject(v) && isString(v.id) && isString(v.label);
const isHolding = (v: unknown) => isObject(v) && isString(v.instrument_id) && isString(v.symbol) && isString(v.name);

function isIssue(v: unknown) {
  if (!isObject(v) || !isString(v.id) || !isHolding(v.holding)) return false;
  const { observation: o, exposure: x } = v;
  const exposureOk =
    isObject(x) && ((x.kind === "calculation" && isString(x.value) && isString(x.basis)) ||
      (x.kind === "unavailable" && isString(x.reason)));
  return (
    isObject(o) && isString(o.text) && isString(o.source) && isString(o.observed_at) &&
    isString(v.interpretation) && isString(v.next_question) && exposureOk &&
    ["supported", "partial", "contested", "insufficient"].includes(v.evidence_status as string) &&
    isArrayOf(v.evidence, (e) =>
      isObject(e) && isString(e.id) && isString(e.source) && isString(e.published_at) &&
      isString(e.known_at) && (e.excerpt === null || isString(e.excerpt)))
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
  if (!isObject(h) || !isObject(h.session) || !isString(h.session.date) || !isString(h.snapshot_at)) return { ok: false };
  if (!isString(h.user_timezone) || !isString(h.exchange_timezone)) return { ok: false };
  const c = h.coverage;
  if (!isObject(c) || !isArrayOf(c.checked, isSource) || !isArrayOf(c.failed, isSource)) return { ok: false };
  if ((c.pending !== undefined && !isArrayOf(c.pending, isSource)) || !isArrayOf(c.unpriced, isHolding)) return { ok: false };
  if (!SURFACE_STATUSES.includes(v.status as SurfaceStatus)) return { ok: false };
  if (!isArrayOf(v.issues, isIssue) || (v.issues as unknown[]).length > 3) return { ok: false };
  const eventsOk = isArrayOf(v.upcoming_events, (e) =>
    isObject(e) && isString(e.id) && isHolding(e.holding) && isString(e.title) && isString(e.at));
  if (!eventsOk) return { ok: false };
  const s = v.last_good_snapshot;
  if (s !== undefined && !(isObject(s) && isString(s.brief_id) && isString(s.snapshot_at) && isArrayOf(s.issues, isIssue))) {
    return { ok: false };
  }
  return { ok: true, view: v as unknown as TodayView };
}
