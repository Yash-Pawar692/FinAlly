import { expect, test } from "@playwright/test";
import { restartAppContainer } from "./helpers/dockerRestart";

// One long, ordered journey against a single shared backend instance (no
// per-test DB reset — see docker-compose.test.yml), matching the scenarios
// in PLAN.md §12. Steps build on each other's state deliberately.
test.setTimeout(120_000);

test("FinAlly end-to-end trading session", async ({ page }) => {
  await test.step("Fresh start: default watchlist, $10k cash, prices streaming", async () => {
    await page.goto("/");

    await expect(page.getByTestId("connection-status")).toHaveText("Connected", { timeout: 15_000 });
    await expect(page.getByTestId("watchlist-row")).toHaveCount(10);
    await expect(page.getByTestId("cash-balance")).toHaveText("$10,000.00");

    const aaplPrice = page.getByTestId("watchlist-row").filter({ hasText: "AAPL" }).getByTestId("watchlist-price");
    await expect(aaplPrice).not.toHaveText("—", { timeout: 5_000 });
  });

  await test.step("Add and remove a watchlist ticker", async () => {
    await page.getByPlaceholder("Add ticker…").fill("PYPL");
    await page.getByRole("button", { name: "Add" }).click();

    const pyplRow = page.locator('[data-testid="watchlist-row"][data-ticker="PYPL"]');
    await expect(pyplRow).toBeVisible();

    await pyplRow.hover();
    await pyplRow.getByRole("button", { name: /remove pypl/i }).click();
    await expect(pyplRow).toHaveCount(0);
  });

  await test.step("Buy shares: cash decreases, position appears", async () => {
    await page.getByTestId("trade-ticker-input").fill("AAPL");
    await page.getByTestId("trade-qty-input").fill("2");
    await page.getByRole("button", { name: "Buy" }).click();

    const positionRow = page.locator('[data-testid="position-row"][data-ticker="AAPL"]');
    await expect(positionRow).toBeVisible();
    await expect(positionRow.getByTestId("position-qty")).toHaveText("2");
    await expect(page.getByTestId("cash-balance")).not.toHaveText("$10,000.00");
  });

  await test.step("Sell shares: position updates rather than disappearing", async () => {
    await page.getByTestId("trade-ticker-input").fill("AAPL");
    await page.getByTestId("trade-qty-input").fill("1");
    await page.getByRole("button", { name: "Sell" }).click();

    const positionRow = page.locator('[data-testid="position-row"][data-ticker="AAPL"]');
    await expect(positionRow.getByTestId("position-qty")).toHaveText("1");
  });

  await test.step("Portfolio visualizations render", async () => {
    await expect(page.getByTestId("heatmap").getByText("AAPL")).toBeVisible();
    // Two trades have landed snapshots by now, so the P&L chart has data.
    await expect(page.getByText("Accumulating history…")).toHaveCount(0);
  });

  await test.step("AI chat (mocked): trade executes and appears inline", async () => {
    await page.getByPlaceholder("Ask FinAlly…").fill("buy 1 TSLA");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.getByText(/✓ BUY 1 TSLA/)).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="position-row"][data-ticker="TSLA"]')).toBeVisible();
  });

  await test.step("Reject a manual trade: error surfaces visibly", async () => {
    await page.getByTestId("trade-ticker-input").fill("AAPL");
    await page.getByTestId("trade-qty-input").fill("999999");
    await page.getByRole("button", { name: "Sell" }).click();

    await expect(page.getByTestId("trade-error")).toContainText("Cannot sell");
  });

  await test.step("SSE resilience: disconnect and reconnect around a container restart", async () => {
    restartAppContainer();

    await expect(page.getByTestId("connection-status")).toHaveText(/Reconnecting|Disconnected/, {
      timeout: 20_000,
    });
    await expect(page.getByTestId("connection-status")).toHaveText("Connected", { timeout: 60_000 });

    const aaplPrice = page.getByTestId("watchlist-row").filter({ hasText: "AAPL" }).getByTestId("watchlist-price");
    const priceBeforeReconnect = await aaplPrice.textContent();
    await expect(async () => {
      expect(await aaplPrice.textContent()).not.toBe(priceBeforeReconnect);
    }).toPass({ timeout: 15_000 });
  });
});
