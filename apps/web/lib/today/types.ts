// View model for the Today page. Hand-authored fixtures fill it until the /briefs API exists.
// Times are UTC ISO strings; the UI formats them, it never computes portfolio values.

export const SURFACE_STATUSES = ["ready", "running", "partial", "stale", "failed", "no_material_change"] as const;
export type SurfaceStatus = (typeof SURFACE_STATUSES)[number];

export type EvidenceStatus = "supported" | "partial" | "contested" | "insufficient";

export const SESSION_NAMES = ["pre_market", "regular", "after_hours", "closed"] as const;
export type SessionName = (typeof SESSION_NAMES)[number];

export interface SourceRef {
  id: string;
  label: string;
}

export interface Holding {
  instrument_id: string;
  symbol: string;
  name: string;
}

export interface TodayHeader {
  session: { name: SessionName; date: string };
  user_timezone: string;
  exchange_timezone: string;
  /** Data cutoff for this brief (UTC). */
  snapshot_at: string;
  coverage: {
    checked: SourceRef[];
    failed: SourceRef[];
    /** Sources still being checked; running only. */
    pending?: SourceRef[];
    unpriced: Holding[];
  };
}

/** A fact: what a source said, and when. */
export interface Observation {
  text: string;
  source: string;
  observed_at: string;
}

/** Precomputed upstream; the UI only displays it. */
export type Exposure =
  | { kind: "calculation"; value: string; basis: string }
  | { kind: "unavailable"; reason: string };

export interface EvidenceItem {
  id: string;
  source: string;
  published_at: string;
  known_at: string;
  /** null when the source isn't licensed for display. */
  excerpt: string | null;
}

export interface Issue {
  id: string;
  holding: Holding;
  observation: Observation;
  interpretation: string;
  evidence_status: EvidenceStatus;
  exposure: Exposure;
  next_question: string;
  evidence: EvidenceItem[];
}

export interface UpcomingEvent {
  id: string;
  holding: Holding;
  title: string;
  at: string;
}

export interface LastGoodSnapshot {
  brief_id: string;
  snapshot_at: string;
  issues: Issue[];
}

export interface TodayView {
  header: TodayHeader;
  status: SurfaceStatus;
  issues: Issue[];
  upcoming_events: UpcomingEvent[];
  /** stale and failed only; never rendered as current. */
  last_good_snapshot?: LastGoodSnapshot;
}

/** One file in fixtures/today/: the contract brief plus the view it produces. */
export interface TodayFixture {
  brief: Record<string, unknown>;
  view: TodayView;
}
