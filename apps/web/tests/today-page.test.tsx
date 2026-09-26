import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import Home from "../app/page";
import { TodayPage } from "../components/today/TodayPage";
import { loadToday, parseToday } from "../lib/today/load";
import type { TodayView } from "../lib/today/types";

afterEach(cleanup);

const renderState = (state: string) => render(<TodayPage result={loadToday(state)} />);

/** The last good brief sits in its own labeled section, never among current issues. */
function expectLastGoodSnapshotApart(root: HTMLElement, time: string) {
  const section = screen.getByRole("heading", { level: 2, name: "Last complete brief (not current)" }).closest("section")!;
  expect(section.getAttribute("data-snapshot")).toBe("previous");
  expect(section.textContent).toContain(`Data as of ${time}`);
  expect(within(section).queryAllByRole("article")).toHaveLength(0);
  const current = root.querySelector("section[aria-labelledby='changes-heading']");
  if (current) expect(current.contains(section)).toBe(false);
}

/** Confidence percentages, trade calls to action, and urgency never appear on Today. */
function expectNoForbiddenContent(root: HTMLElement) {
  const text = root.textContent ?? "";
  expect(text).not.toMatch(/\d\s*%[^.]*\b(confiden|sure|certain|likel|probab|chance)/i);
  expect(text).not.toMatch(/\b(confiden|sure|certain|probab|chance)\w*[^.]*\d\s*%/i);
  expect(text).not.toMatch(/\b(urgent|act now|hurry|don't miss|countdown)\b/i);
  const actions = [...root.querySelectorAll("a, button")].map((el) => el.textContent ?? "");
  for (const label of actions) expect(label).not.toMatch(/\b(buy|sell|trade|order)\b/i);
}

describe("header", () => {
  test("shows session, snapshot time in exchange and local time, and coverage", () => {
    renderState("ready");
    expect(screen.getByRole("heading", { level: 1, name: "Today" })).toBeTruthy();
    expect(screen.getByText("Pre-market · Monday, September 28, 2026")).toBeTruthy();
    expect(screen.getByText("Mon, Sep 28, 7:30 AM EDT")).toBeTruthy();
    expect(screen.getByText(/Mon, 4:30 AM PDT your time/)).toBeTruthy();
    expect(screen.getByTestId("coverage-line").textContent).toBe(
      "3 sources checked: Company releases, SEC filings, News. Price unavailable for SYN03.",
    );
  });
});

describe("ready", () => {
  test("lists up to three issues under a material-changes heading", () => {
    const { container } = renderState("ready");
    expect(screen.getByRole("heading", { level: 2, name: "Material changes" })).toBeTruthy();
    const issues = screen.getAllByRole("article");
    expect(issues).toHaveLength(3);
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "SYN01 · Synthela 01", "SYN12 · Synthela 12", "SYN03 · Synthela 03",
    ]);
    expectNoForbiddenContent(container);
  });

  test("labels fact, calculation, and interpretation in every issue", () => {
    renderState("ready");
    for (const issue of screen.getAllByRole("article")) {
      const card = within(issue);
      expect(card.getByText("Fact")).toBeTruthy();
      expect(card.getByText("Calculation")).toBeTruthy();
      expect(card.getByText("Interpretation")).toBeTruthy();
      expect(card.getByText("Next research question")).toBeTruthy();
      expect(card.getByRole("link", { name: /^Investigate SYN\d\d$/ })).toBeTruthy();
    }
  });

  test("shows the fact's source and time, and the precomputed exposure", () => {
    renderState("ready");
    const syn01 = within(screen.getAllByRole("article")[0]);
    expect(syn01.getByText(/^Synthela 01 company release ·/).textContent).toBe(
      "Synthela 01 company release · Mon, Sep 28, 6:45 AM EDT (Mon, 3:45 AM PDT your time)",
    );
    expect(syn01.getByText("48.8% of priced portfolio value")).toBeTruthy();
  });

  test("missing price shows exposure as unavailable, never zero", () => {
    renderState("ready");
    const syn03 = screen.getAllByRole("article")[2];
    expect(within(syn03).getByText("Exposure unavailable.")).toBeTruthy();
    expect(syn03.textContent).not.toMatch(/\b0(\.0+)?\s*%|\$0\b/);
  });

  test("warning evidence statuses carry text and an icon", () => {
    renderState("ready");
    const [, syn12, syn03] = screen.getAllByRole("article");
    for (const [card, text] of [[syn12, "Evidence: Contested — sources disagree"], [syn03, "Evidence: Insufficient"]] as const) {
      const label = within(card).getByText(text).parentElement!;
      expect(label.querySelector("svg[aria-hidden='true']")).toBeTruthy();
    }
  });

  test("evidence is collapsed by default and shows both clocks and excerpts", () => {
    renderState("ready");
    const syn12 = screen.getAllByRole("article")[1];
    const details = syn12.querySelector("details")!;
    expect(details.open).toBe(false);
    expect(within(syn12).getByText("Evidence for SYN12 (2 sources)").tagName).toBe("SUMMARY");
    const items = within(details).getAllByRole("listitem");
    expect(within(items[0]).getByText("Published")).toBeTruthy();
    expect(within(items[0]).getByText("Known to us")).toBeTruthy();
    expect(within(items[0]).getByText(/extended for two years/)).toBeTruthy();
    expect(within(items[1]).getByText("Excerpt not licensed for display.")).toBeTruthy();
  });

  test("lists upcoming events in exchange and local time", () => {
    renderState("ready");
    const events = screen.getByRole("heading", { level: 2, name: "Upcoming events" }).parentElement!;
    expect(within(events).getByText("Tue, Sep 29, 4:30 PM EDT (Tue, 1:30 PM PDT your time)")).toBeTruthy();
  });
});

describe("partial", () => {
  test("names the failed source and what the issues are based on", () => {
    const { container } = renderState("partial");
    const notice = screen.getByRole("status");
    expect(notice.textContent).toContain("Partial brief");
    expect(notice.textContent).toContain("News couldn't be checked. The issues below come from Company releases, SEC filings only");
    expect(notice.querySelector("svg[aria-hidden='true']")).toBeTruthy();
    expect(screen.getByTestId("coverage-line").textContent).toContain("1 source failed: News.");
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.queryByText(/No new material changes/)).toBeNull();
    expectNoForbiddenContent(container);
  });
});

describe("failed", () => {
  test("shows no current results, an explicit retry, and the last good brief apart", () => {
    const { container } = renderState("failed");
    expect(screen.getByText("Attempted cutoff")).toBeTruthy();
    expect(screen.queryByText("Data as of")).toBeNull();
    const notice = screen.getByRole("status");
    expect(notice.textContent).toContain("This morning's brief didn't complete");
    expect(notice.textContent).toContain("No sources could be checked.");
    expect(within(notice).getByRole("link", { name: "Retry" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Material changes" })).toBeNull();
    expect(screen.queryAllByRole("article")).toHaveLength(0);
    expectLastGoodSnapshotApart(container, "Fri, Sep 25, 5:00 PM EDT (Fri, 2:00 PM PDT your time)");
    expectNoForbiddenContent(container);
  });
});

describe("stale", () => {
  test("says the data is out of date and keeps the last good brief apart", () => {
    const { container } = renderState("stale");
    const notice = screen.getByRole("status");
    expect(notice.textContent).toContain("This brief is out of date");
    expect(notice.textContent).toContain("The newest complete data is from Fri, Sep 25, 5:00 PM EDT");
    expect(notice.textContent).toContain("nothing here is current");
    expect(notice.querySelector("svg[aria-hidden='true']")).toBeTruthy();
    expect(within(notice).getByRole("link", { name: "Retry" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Material changes" })).toBeNull();
    expectLastGoodSnapshotApart(container, "Fri, Sep 25, 5:00 PM EDT (Fri, 2:00 PM PDT your time)");
    expectNoForbiddenContent(container);
  });
});

describe("running", () => {
  test("says what's checked and pending, with no results or clean-day copy", () => {
    const { container } = renderState("running");
    expect(screen.getByText("Checking data up to")).toBeTruthy();
    const notice = screen.getByRole("status");
    expect(notice.textContent).toContain("Brief in progress");
    expect(notice.textContent).toContain("Checked so far: Company releases. Still checking: SEC filings, News.");
    expect(screen.getByTestId("coverage-line").textContent).toContain("Still checking: SEC filings, News.");
    expect(screen.queryAllByRole("article")).toHaveLength(0);
    expect(screen.queryByText(/No new material changes/)).toBeNull();
    expect(screen.queryByRole("heading", { name: /Last complete brief/ })).toBeNull();
    expectNoForbiddenContent(container);
  });
});

describe("no_material_change", () => {
  test("stays quiet and offers monitored coverage", () => {
    const { container } = renderState("no_material_change");
    const notice = screen.getByRole("status");
    expect(within(notice).getByText("No new material changes found within current coverage.")).toBeTruthy();
    const summary = within(notice).getByText("View monitored coverage");
    expect(summary.tagName).toBe("SUMMARY");
    expect((summary.parentElement as HTMLDetailsElement).open).toBe(false);
    expect(notice.textContent).toContain("News: checked");
    expect(notice.textContent).toContain("SYN03 (Synthela 03): price unavailable");
    expect(notice.querySelector("svg")).toBeNull();
    expect(screen.queryAllByRole("article")).toHaveLength(0);
    expectNoForbiddenContent(container);
  });

  const quietView = () => {
    const result = loadToday("no_material_change");
    if (!result.ok) throw new Error("fixture should load");
    return structuredClone(result.view);
  };

  test.each([
    ["a source failed", (v: TodayView) => { v.header.coverage.failed = [v.header.coverage.checked.pop()!]; }, "News couldn't be checked"],
    ["coverage is empty", (v: TodayView) => { v.header.coverage.checked = []; }, "No sources were checked"],
  ])("is never shown when %s", (_, mutate, reason) => {
    const view = quietView();
    mutate(view);
    render(<TodayPage result={{ ok: true, view }} />);
    expect(screen.queryByText(/No new material changes/)).toBeNull();
    expect(screen.queryByText("View monitored coverage")).toBeNull();
    const notice = screen.getByRole("status");
    expect(notice.textContent).toContain("Coverage incomplete");
    expect(notice.textContent).toContain(reason);
  });
});

describe("unreadable fixture", () => {
  test("says Today couldn't load and shows no financial content", () => {
    const { container } = renderState("unreadable");
    expect(screen.getByRole("heading", { level: 1, name: "Today couldn't load" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Retry" })).toBeTruthy();
    expect(container.textContent).not.toMatch(/SYN\d|%|\$|Evidence|Fact/);
  });

  test.each([null, {}, { view: { status: "ready" } }, "not json"])("rejects %j at the boundary", (raw) => {
    expect(parseToday(raw).ok).toBe(false);
  });

  // ready's issues and events plus stale's last good snapshot cover every timestamp field.
  const datedView = () => {
    const ready = loadToday("ready");
    const stale = loadToday("stale");
    if (!ready.ok || !stale.ok) throw new Error("fixtures should load");
    return structuredClone({ ...ready.view, last_good_snapshot: stale.view.last_good_snapshot });
  };

  test.each([
    ["header.snapshot_at", (v: TodayView) => { v.header.snapshot_at = "not-a-date"; }],
    ["header.snapshot_at without a UTC marker", (v: TodayView) => { v.header.snapshot_at = "2026-09-28T11:30:00"; }],
    ["header.session.date", (v: TodayView) => { v.header.session.date = "Monday"; }],
    ["header.session.date out of range", (v: TodayView) => { v.header.session.date = "2026-02-30"; }],
    ["header.user_timezone", (v: TodayView) => { v.header.user_timezone = "not-a-zone"; }],
    ["header.exchange_timezone", (v: TodayView) => { v.header.exchange_timezone = "not-a-zone"; }],
    ["issues[].observation.observed_at", (v: TodayView) => { v.issues[0].observation.observed_at = "yesterday"; }],
    ["issues[].evidence[].published_at", (v: TodayView) => { v.issues[0].evidence[0].published_at = "not-a-date"; }],
    ["issues[].evidence[].known_at", (v: TodayView) => { v.issues[0].evidence[0].known_at = "2026-13-01T00:00:00Z"; }],
    ["upcoming_events[].at", (v: TodayView) => { v.upcoming_events[0].at = "soon"; }],
    ["last_good_snapshot.snapshot_at", (v: TodayView) => { v.last_good_snapshot!.snapshot_at = "not-a-date"; }],
    ["last_good_snapshot.issues[].observation.observed_at", (v: TodayView) => {
      v.last_good_snapshot!.issues[0].observation.observed_at = "not-a-date";
    }],
    ["last_good_snapshot.issues[].evidence[].known_at", (v: TodayView) => {
      v.last_good_snapshot!.issues[0].evidence[0].known_at = "not-a-date";
    }],
  ])("rejects a malformed %s", (_, mutate) => {
    const view = datedView();
    expect(parseToday({ view }).ok).toBe(true);
    mutate(view);
    expect(parseToday({ view }).ok).toBe(false);
  });

  // Prototype keys like "__proto__" would otherwise resolve to an inherited value in SESSION_LABELS.
  test.each([
    ["missing", undefined],
    ["unknown", "overnight"],
    ["wrong-type", 1],
    ["prototype-key __proto__", "__proto__"],
    ["prototype-key constructor", "constructor"],
  ])("rejects a session name that is %s, showing only couldn't load", (_, name) => {
    const view = datedView() as unknown as { header: { session: Record<string, unknown> } };
    view.header.session.name = name;
    const result = parseToday({ view });
    expect(result.ok).toBe(false);
    const { container } = render(<TodayPage result={result} />);
    expect(screen.getByRole("heading", { level: 1, name: "Today couldn't load" })).toBeTruthy();
    expect(container.textContent).not.toMatch(/SYN\d|%|\$|Evidence|Fact/);
  });
});

describe("route", () => {
  test("defaults to the ready fixture and shows the development switcher", async () => {
    render(await Home({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1, name: "Today" })).toBeTruthy();
    const nav = screen.getByRole("navigation", { name: "Fixture state (development only)" });
    expect(within(nav).getByRole("link", { name: "ready" }).getAttribute("aria-current")).toBe("page");
  });
});
