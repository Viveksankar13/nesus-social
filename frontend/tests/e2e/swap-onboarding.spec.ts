import { test, expect } from "@playwright/test";

test.describe("Skill Swap Economy — S1 Onboarding & Discovery Hub", () => {
  test("Swaps hub page renders hero banner and canonical taxonomy", async ({
    page,
  }) => {
    await page.goto("/swaps");

    // Verify hero headline
    await expect(page.locator("text=Hyper-Local Skill Swap Economy").first()).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: /Exchange 30 Minutes of Peer Help/i,
      })
    ).toBeVisible();

    // Verify discovery actions
    await expect(page.locator("text=Create Swap Offer").first()).toBeVisible();
  });

  test("Onboarding wizard page renders 4 progress steps", async ({
    page,
  }) => {
    await page.goto("/swaps/onboarding");

    // Verify onboarding header
    await expect(
      page.getByRole("heading", {
        name: /Welcome to the Skill Swap Economy/i,
      })
    ).toBeVisible();

    // Verify 4 steps
    await expect(page.locator("text=I Can Teach").first()).toBeVisible();
    await expect(page.locator("text=I Want to Learn").first()).toBeVisible();
    await expect(page.locator("text=Availability").first()).toBeVisible();
    await expect(page.locator("text=Preferences").first()).toBeVisible();

    // Step 1 title
    await expect(
      page.getByRole("heading", {
        name: /What skills can you teach or share/i,
      })
    ).toBeVisible();
  });
});
