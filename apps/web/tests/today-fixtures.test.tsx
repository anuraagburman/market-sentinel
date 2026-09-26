// @vitest-environment node
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import { describe, expect, test } from "vitest";
import { type TodayFixture, type TodayView } from "../lib/today/types";

const repo = fileURLToPath(new URL("../../../", import.meta.url));
const schemaDir = join(repo, "packages/contracts/schemas");
const fixtureDir = fileURLToPath(new URL("../fixtures/today/", import.meta.url));

const readJson = (path: string) => JSON.parse(readFileSync(path, "utf8"));

// Type/required strictness off: the contract's if/then subschemas omit "type" and restate
// "required" by design (valid 2020-12). Unknown keywords still fail.
const ajv = new Ajv2020({ strict: true, strictTypes: false, strictRequired: false, allErrors: true });
addFormats(ajv);
for (const file of readdirSync(schemaDir).filter((f) => f.endsWith(".schema.json"))) {
  ajv.addSchema(readJson(join(schemaDir, file)));
}
const validateBrief = ajv.getSchema("https://market-sentinel.local/schemas/brief.schema.json")!;

const positions: { portfolio_version_id: string; instrument_id: string; display_symbol: string }[] = readJson(
  join(repo, "evals/fixtures/portfolio/positions.json"),
);
const symbolById = new Map(positions.map((p) => [p.instrument_id, p.display_symbol]));

// unreadable.json deliberately fails the view shape check; it backs the "couldn't load" state.
const fixtures = readdirSync(fixtureDir)
  .filter((f) => f.endsWith(".json") && f !== "unreadable.json")
  .map((f) => ({ state: f.replace(/\.json$/, ""), fixture: readJson(join(fixtureDir, f)) as TodayFixture }));

function holdingsIn(view: TodayView) {
  const issues = [...view.issues, ...(view.last_good_snapshot?.issues ?? [])];
  return [
    ...issues.map((i) => i.holding),
    ...view.upcoming_events.map((e) => e.holding),
    ...view.header.coverage.unpriced,
  ];
}

describe.each(fixtures)("$state fixture", ({ state, fixture }) => {
  test("brief validates against the v1 schema with formats", () => {
    const ok = validateBrief(fixture.brief);
    expect(validateBrief.errors ?? []).toEqual([]);
    expect(ok).toBe(true);
  });

  test("brief and view agree on status, cutoff, and coverage", () => {
    const { brief, view } = fixture;
    const coverage = brief.coverage as { checked_sources: string[]; failed_sources: string[]; unpriced_instrument_ids?: string[] };
    expect(view.status).toBe(state);
    expect(brief.status).toBe(state);
    expect(view.header.snapshot_at).toBe(brief.cutoff);
    expect(view.header.coverage.checked.map((s) => s.id)).toEqual(coverage.checked_sources);
    expect(view.header.coverage.failed.map((s) => s.id)).toEqual(coverage.failed_sources);
    expect(view.header.coverage.unpriced.map((h) => h.instrument_id)).toEqual(coverage.unpriced_instrument_ids ?? []);
  });

  test("every instrument id resolves against the portfolio fixture", () => {
    const { brief, view } = fixture;
    expect(brief.portfolio_version_id).toBe(positions[0].portfolio_version_id);
    for (const holding of holdingsIn(view)) {
      expect(symbolById.get(holding.instrument_id), holding.instrument_id).toBe(holding.symbol);
    }
  });

  test("respects the view-model shape limits", () => {
    const { view } = fixture;
    expect(view.issues.length).toBeLessThanOrEqual(3);
    if (view.last_good_snapshot) expect(["stale", "failed"]).toContain(state);
  });
});
