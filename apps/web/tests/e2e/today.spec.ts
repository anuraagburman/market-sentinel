import { expect, type Page, test } from "@playwright/test";

const STATES = ["ready", "running", "partial", "stale", "failed", "no_material_change"];

async function blockExternal(page: Page) {
  const external: string[] = [];
  await page.route("**/*", async (route) => {
    if (new URL(route.request().url()).hostname !== "127.0.0.1") {
      external.push(route.request().url());
      await route.abort();
    } else {
      await route.continue();
    }
  });
  return external;
}

for (const state of ["ready", "partial"]) {
  test(`${state} renders with no external requests`, async ({ page }) => {
    const external = await blockExternal(page);
    await page.goto(`/?state=${state}`);
    await expect(page.getByRole("heading", { level: 1, name: "Today" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Material changes" })).toBeVisible();
    await expect(page.getByText("Research and paper decisions only. No live orders.")).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(external).toEqual([]);
  });
}

test("keyboard focus reaches every issue's evidence disclosure, which expands and collapses", async ({ page }) => {
  await page.goto("/?state=ready");
  const summaries = page.locator("article summary");
  await expect(summaries).toHaveCount(3);
  const labels = await summaries.allTextContents();

  const reached: string[] = [];
  for (let i = 0; i < 60 && reached.length < labels.length; i++) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const el = document.activeElement;
      return el?.tagName === "SUMMARY" ? el.textContent : null;
    });
    if (focused && !reached.includes(focused)) reached.push(focused);
  }
  expect(reached).toEqual(labels);

  // Focus is on the last issue's summary: Enter toggles it without a pointer.
  const details = page.locator("article details").last();
  const excerpt = details.getByText(/could not complete its quarterly report/);
  await expect(excerpt).toBeHidden();
  await page.keyboard.press("Enter");
  await expect(details).toHaveAttribute("open", "");
  await expect(excerpt).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(details).not.toHaveAttribute("open", "");
  await expect(excerpt).toBeHidden();
});

test.describe("mobile width", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  for (const state of STATES) {
    test(`${state} has no horizontal scroll at 390px`, async ({ page }) => {
      await page.goto(`/?state=${state}`);
      await page.locator("details").evaluateAll((els) => els.forEach((el) => ((el as HTMLDetailsElement).open = true)));
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(0);
    });
  }
});
