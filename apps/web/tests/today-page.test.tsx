import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import Home from "../app/page";
import { TodayPage } from "../components/today/TodayPage";
import { loadToday } from "../lib/today/load";

afterEach(cleanup);

const renderState = (state: string) => render(<TodayPage result={loadToday(state)} />);

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
    expect(syn01.getByText(/^Synthela 01 company release ·/)).toBeTruthy();
    expect(syn01.getByText("Mon, Sep 28, 6:45 AM EDT (Mon, 3:45 AM PDT your time)")).toBeTruthy();
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

  test("lists upcoming events in exchange and local time", () => {
    renderState("ready");
    const events = screen.getByRole("heading", { level: 2, name: "Upcoming events" }).parentElement!;
    expect(within(events).getByText("Tue, Sep 29, 4:30 PM EDT (Tue, 1:30 PM PDT your time)")).toBeTruthy();
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
