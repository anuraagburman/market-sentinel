import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import Home from "../app/page";

afterEach(cleanup);
test("identifies product and research-only boundary", () => {
  render(<Home />);
  expect(screen.getByRole("heading", { name: "Market Sentinel", level: 1 })).toBeTruthy();
  expect(screen.getByText("Research and paper decisions only. No live orders.")).toBeTruthy();
});
