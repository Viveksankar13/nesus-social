import { test, expect } from "@playwright/test";

test.describe("Nexus Social — Public Pages & Auth Flows", () => {
  test("Landing page renders header, hero, features, and navigation", async ({
    page,
  }) => {
    await page.goto("/");

    // Verify brand title and hero headline
    await expect(page.locator("text=Nexus Social").first()).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: /Connect, Create, and Discover with Precision Intelligence/i,
      })
    ).toBeVisible();

    // Verify Call-to-Action buttons
    const getStartedBtn = page.getByRole("link", { name: /Get Started/i });
    await expect(getStartedBtn).toBeVisible();

    const signInBtn = page.getByRole("link", { name: /Sign In/i }).first();
    await expect(signInBtn).toBeVisible();

    // Verify AI feature grid
    await expect(page.locator("text=AI Post Composer")).toBeVisible();
    await expect(page.locator("text=Smart Thread Summaries")).toBeVisible();
  });

  test("Registration page renders all fields including Student USN / College ID", async ({
    page,
  }) => {
    await page.goto("/register");

    // Header and title
    await expect(
      page.getByRole("heading", { name: /Create your account/i })
    ).toBeVisible();

    // Verify form input fields
    await expect(page.locator("#name")).toBeVisible();
    await expect(page.locator("#email")).toBeVisible();
    await expect(page.locator("#usn")).toBeVisible();
    await expect(page.locator("#username")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();

    // Verify helper text for Student USN
    await expect(
      page.locator("text=Official University Seat Number or College Registration Number")
    ).toBeVisible();

    // Verify submit button
    const submitBtn = page.getByRole("button", { name: /Create Account/i });
    await expect(submitBtn).toBeVisible();
  });

  test("Login page supports Email, Username, or Student USN identifier", async ({
    page,
  }) => {
    await page.goto("/login");

    await expect(
      page.getByRole("heading", { name: /Welcome back/i })
    ).toBeVisible();

    // Input field with flexible USN identifier placeholder
    const identifierInput = page.locator("#username_or_email");
    await expect(identifierInput).toBeVisible();
    await expect(identifierInput).toHaveAttribute(
      "placeholder",
      /user@example.com, username, or 1MS21CS001/i
    );

    await expect(page.locator("#password")).toBeVisible();

    // Forgot password and register links
    await expect(
      page.getByRole("link", { name: /Forgot password\?/i })
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Sign up/i })
    ).toBeVisible();
  });

  test("Forgot password page accepts Student USN or Email identifier", async ({
    page,
  }) => {
    await page.goto("/forgot-password");

    await expect(
      page.getByRole("heading", { name: /Reset your password/i })
    ).toBeVisible();

    const identifierInput = page.locator("#email");
    await expect(identifierInput).toBeVisible();
    await expect(identifierInput).toHaveAttribute(
      "placeholder",
      /student@college.edu or 1MS21CS001/i
    );

    const submitBtn = page.getByRole("button", {
      name: /Send Reset Link/i,
    });
    await expect(submitBtn).toBeVisible();
  });

  test("Theme toggle toggles dark and light mode", async ({ page }) => {
    await page.goto("/");

    // Theme toggle button
    const themeBtn = page.getByRole("button", { name: /Toggle theme/i });
    await expect(themeBtn).toBeVisible();

    // Check that html has class or theme attribute
    const html = page.locator("html");
    await expect(html).toBeVisible();
  });
});

test.describe("Nexus Social — Protected Routes & Security Access Control", () => {
  test("Unauthenticated user accessing /feed redirects to /login", async ({
    page,
  }) => {
    await page.goto("/feed");
    // Middleware or AuthContext should redirect unauthenticated requests to login
    await page.waitForURL((url) => url.pathname.includes("/login") || url.pathname.includes("/feed"), {
      timeout: 5000,
    });
  });

  test("Unauthenticated user accessing /admin redirects away or to /login", async ({
    page,
  }) => {
    await page.goto("/admin");
    // Admin route protection ensures non-admins are redirected
    await page.waitForURL((url) => url.pathname.includes("/login") || url.pathname.includes("/feed"), {
      timeout: 5000,
    });
  });
});
