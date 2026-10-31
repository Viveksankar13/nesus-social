import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const ARTIFACT_DIR = "C:\\Users\\BRENWEN\\.gemini\\antigravity\\brain\\ef3e3560-ae99-4f2b-a134-74e48999f2c5\\screenshots";

if (!fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

async function capture() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  console.log("Navigating to /swaps...");
  await page.goto("http://localhost:3000/swaps", { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(ARTIFACT_DIR, "stage1_swaps_hub.png"), fullPage: true });
  console.log("Captured stage1_swaps_hub.png");

  console.log("Navigating to /swaps/onboarding...");
  await page.goto("http://localhost:3000/swaps/onboarding", { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(ARTIFACT_DIR, "stage1_onboarding_step1.png"), fullPage: true });
  console.log("Captured stage1_onboarding_step1.png");

  // Advance to step 2
  const continueBtn = page.getByRole("button", { name: /Continue/i });
  if (await continueBtn.isVisible()) {
    await continueBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "stage1_onboarding_step2.png"), fullPage: true });
    console.log("Captured stage1_onboarding_step2.png");
  }

  // Advance to step 3
  if (await continueBtn.isVisible()) {
    await continueBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "stage1_onboarding_step3_availability.png"), fullPage: true });
    console.log("Captured stage1_onboarding_step3_availability.png");
  }

  // Advance to step 4
  if (await continueBtn.isVisible()) {
    await continueBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "stage1_onboarding_step4_privacy.png"), fullPage: true });
    console.log("Captured stage1_onboarding_step4_privacy.png");
  }

  console.log("Navigating to /settings/swaps...");
  await page.goto("http://localhost:3000/settings/swaps", { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(ARTIFACT_DIR, "stage1_swap_settings.png"), fullPage: true });
  console.log("Captured stage1_swap_settings.png");

  await browser.close();
  console.log("All screenshots captured successfully!");
}

capture().catch((err) => {
  console.error("Capture error:", err);
  process.exit(1);
});
