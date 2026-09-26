import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import Home from "../app/page";
import { TodayPage } from "../components/today/TodayPage";
import { loadToday } from "../lib/today/load";

afterEach(cleanup);

const renderState = (state: string) => render(<TodayPage result={loadToday(state)} />);

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

describe("route", () => {
  test("defaults to the ready fixture and shows the development switcher", async () => {
    render(await Home({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1, name: "Today" })).toBeTruthy();
    const nav = screen.getByRole("navigation", { name: "Fixture state (development only)" });
    expect(within(nav).getByRole("link", { name: "ready" }).getAttribute("aria-current")).toBe("page");
  });
});
