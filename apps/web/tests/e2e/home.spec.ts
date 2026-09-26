import { expect, test } from "@playwright/test";

test("placeholder page loads without external requests", async ({ page }) => {
  const externalRequests: string[] = [];
  await page.route("**/*", async (route) => {
    if (new URL(route.request().url()).hostname !== "127.0.0.1") {
      externalRequests.push(route.request().url());
      await route.abort();
    } else { await route.continue(); }
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Market Sentinel" })).toBeVisible();
  await expect(page.getByText("Research and paper decisions only. No live orders.")).toBeVisible();
  expect(externalRequests).toEqual([]);
});
