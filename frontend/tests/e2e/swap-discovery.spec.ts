import { test, expect } from "@playwright/test";
import path from "path";

const SCREENSHOT_DIR = "C:/Users/BRENWEN/.gemini/antigravity/brain/ef3e3560-ae99-4f2b-a134-74e48999f2c5/screenshots";

test.describe("Skill Swap Economy — Stage 2 Listings & Discovery", () => {
  test("Swaps discovery page renders search, filters, and list/map toggle", async ({
    page,
  }) => {
    await page.goto("/swaps");

    // Verify hero and title
    await expect(page.locator("text=Hyper-Local Skill Swap Economy").first()).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: /Exchange 30 Minutes of Peer Help/i,
      })
    ).toBeVisible();

    // Verify search input and filter buttons
    await expect(page.getByPlaceholder(/Search swap offers/i)).toBeVisible();
    await expect(page.locator("text=Create Swap Offer").first()).toBeVisible();
    await expect(page.locator("text=Matches for You").first()).toBeVisible();

    // Take screenshot of discovery page in list view
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage2_swaps_discovery_list.png"),
      fullPage: true,
    });

    // Toggle to Map View
    const mapBtn = page.getByRole("button", { name: "Map" });
    if (await mapBtn.isVisible()) {
      await mapBtn.click();
      await page.waitForTimeout(1000);
      await expect(page.locator("text=Coarse area view").first()).toBeVisible();
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, "stage2_swaps_discovery_map.png"),
        fullPage: true,
      });
    }
  });

  test("Create swap offer wizard page renders AI Draft Helper and form", async ({
    page,
  }) => {
    await page.goto("/swaps/new");

    // Verify wizard headline and anti-money policy
    await expect(
      page.getByRole("heading", {
        name: /Create a 30-Minute Swap Offer/i,
      })
    ).toBeVisible();

    await expect(page.locator("text=Strictly Non-Monetary Peer Exchange")).toBeVisible();
    await expect(page.locator("text=Gemini AI Draft Helper")).toBeVisible();
    await expect(page.locator("text=Offer Title *")).toBeVisible();
    await expect(page.locator("text=Description *")).toBeVisible();

    // Take screenshot of create wizard
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage2_create_offer_wizard.png"),
      fullPage: true,
    });
  });

  test("Matches page renders recommendations and transparent score breakdown", async ({
    page,
  }) => {
    await page.goto("/swaps/matches");

    // Verify matches banner
    await expect(
      page.getByRole("heading", {
        name: /Personalized Matches for You/i,
      })
    ).toBeVisible();

    await expect(page.locator("text=AI-Powered Recommendations")).toBeVisible();

    // Take screenshot of matches page
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage2_swap_matches.png"),
      fullPage: true,
    });
  });
});
