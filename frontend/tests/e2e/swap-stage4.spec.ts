import { test, expect } from "@playwright/test";
import path from "path";

const SCREENSHOT_DIR =
  "C:/Users/BRENWEN/.gemini/antigravity/brain/ef3e3560-ae99-4f2b-a134-74e48999f2c5/screenshots";

const MOCK_ADMIN_USER = {
  id: "admin-uuid-123",
  username: "system_admin",
  email: "admin@nexus.dev",
  display_name: "System Admin",
  avatar_url: null,
  role: "admin",
  is_verified: true,
  is_active: true,
};

const MOCK_SWAP_STATS = {
  total_active_listings: 18,
  swaps_this_week: 12,
  total_scheduled_sessions: 42,
  total_completed_sessions: 38,
  total_disputes: 2,
  completion_rate: 90.5,
  dispute_rate: 4.8,
  top_skills: [
    { skill: "Python Backend Development", count: 14 },
    { skill: "Algorithms & Data Structures", count: 12 },
    { skill: "Conversational French", count: 9 },
    { skill: "Resume & Interview Prep", count: 7 },
    { skill: "Acoustic Guitar Basics", count: 5 },
  ],
};

const MOCK_ADMIN_LISTINGS = [
  {
    id: "list-1",
    title: "Python & FastAPI Architecture for Spanish Practice",
    user: {
      id: "user-1",
      username: "alex_coder",
      display_name: "Alex Rivera",
      avatar_url: null,
    },
    skill_offered: {
      id: "skill-1",
      slug: "python-dev",
      display_name: "Python Backend Development",
      category: "Technology",
      status: "active",
    },
    skill_wanted: {
      id: "skill-2",
      slug: "conversational-spanish",
      display_name: "Conversational Spanish",
      category: "Languages",
      status: "active",
    },
    status: "active",
    modes: ["video"],
    reports_count: 0,
    created_at: new Date().toISOString(),
  },
  {
    id: "list-2",
    title: "Suspicious Commercial Tutor Advertising",
    user: {
      id: "user-bad",
      username: "money_requester",
      display_name: "Spam Account",
      avatar_url: null,
    },
    skill_offered: {
      id: "skill-1",
      slug: "python-dev",
      display_name: "Python Backend Development",
      category: "Technology",
      status: "active",
    },
    skill_wanted: null,
    status: "active",
    modes: ["video"],
    reports_count: 3,
    created_at: new Date().toISOString(),
  },
];

const MOCK_ADMIN_DISPUTES = [
  {
    id: "rep-1",
    session_id: "sess-123",
    reporter: {
      id: "user-2",
      username: "sophia_tech",
      display_name: "Sophia Chen",
      avatar_url: null,
    },
    target_type: "session",
    category: "no_show",
    notes: "Peer never joined the Jitsi room despite agreeing to the slot. Waited 15 minutes.",
    status: "pending",
    created_at: new Date().toISOString(),
  },
];

const MOCK_ADMIN_TAXONOMY = [
  {
    id: "skill-pending-1",
    slug: "quantum-computing",
    display_name: "Quantum Computing & Qiskit",
    category: "Technology",
    aliases: ["quantum", "qiskit"],
    status: "pending",
    created_at: new Date().toISOString(),
  },
  {
    id: "skill-1",
    slug: "python-dev",
    display_name: "Python Backend Development",
    category: "Technology",
    aliases: ["python", "fastapi"],
    status: "active",
    created_at: new Date().toISOString(),
  },
  {
    id: "skill-2",
    slug: "conversational-spanish",
    display_name: "Conversational Spanish",
    category: "Languages",
    aliases: ["spanish"],
    status: "active",
    created_at: new Date().toISOString(),
  },
];

const MOCK_SESSION_FOR_AI = {
  id: "sess-ai-1",
  request_id: "req-1",
  user_a: {
    id: "user-1",
    username: "alex_coder",
    display_name: "Alex Rivera",
    avatar_url: null,
  },
  user_b: {
    id: "admin-uuid-123",
    username: "system_admin",
    display_name: "System Admin",
    avatar_url: null,
  },
  status: "scheduled",
  mode: "video",
  public_place_name: null,
  public_place_address: null,
  jitsi_room_token: "secret-token-123",
  jitsi_room_url: "https://meet.jit.si/nexus-swap-test",
  user_a_confirmed: false,
  user_b_confirmed: false,
  dispute_reason: null,
  halves: [
    {
      id: "half-1",
      session_id: "sess-ai-1",
      half_number: 1,
      mentor: { id: "user-1", username: "alex_coder", display_name: "Alex Rivera" },
      learner: { id: "admin-uuid-123", username: "system_admin", display_name: "System Admin" },
      skill: { id: "skill-1", slug: "python-dev", display_name: "Python Backend Development", category: "Technology", status: "active" },
      start_time_utc: new Date(Date.now() + 3600000).toISOString(),
      end_time_utc: new Date(Date.now() + 5400000).toISOString(),
      status: "scheduled",
      ics_uid: "ics-1",
    },
    {
      id: "half-2",
      session_id: "sess-ai-1",
      half_number: 2,
      mentor: { id: "admin-uuid-123", username: "system_admin", display_name: "System Admin" },
      learner: { id: "user-1", username: "alex_coder", display_name: "Alex Rivera" },
      skill: { id: "skill-2", slug: "conversational-spanish", display_name: "Conversational Spanish", category: "Languages", status: "active" },
      start_time_utc: new Date(Date.now() + 5400000).toISOString(),
      end_time_utc: new Date(Date.now() + 7200000).toISOString(),
      status: "scheduled",
      ics_uid: "ics-2",
    },
  ],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

test.describe("Stage 4: Safety, Admin & AI Helpers", () => {
  test.beforeEach(async ({ page, context }) => {
    // Add auth cookies required by Next.js middleware for admin routes
    await context.addCookies([
      {
        name: "refresh_token",
        value: "dummy_admin_refresh_token",
        domain: "localhost",
        path: "/",
      },
      {
        name: "user_role",
        value: "admin",
        domain: "localhost",
        path: "/",
      },
    ]);

    // Mock auth refresh
    await page.route("**/api/v1/auth/refresh", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "dummy_admin_access_token",
          user: MOCK_ADMIN_USER,
        }),
      });
    });

    // Mock user auth
    await page.route("**/api/v1/users/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_ADMIN_USER),
      });
    });

    // Mock Admin Swaps routes
    await page.route("**/api/v1/admin/swaps/stats", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_SWAP_STATS),
      });
    });

    await page.route("**/api/v1/admin/swaps/listings*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_ADMIN_LISTINGS),
      });
    });

    await page.route("**/api/v1/admin/swaps/disputes*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_ADMIN_DISPUTES),
      });
    });

    await page.route("**/api/v1/admin/swaps/taxonomy*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_ADMIN_TAXONOMY),
      });
    });

    // Mock Session routes
    await page.route("**/api/v1/swaps/sessions/sess-ai-1", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_SESSION_FOR_AI),
      });
    });

    await page.route("**/api/v1/swaps/sessions/sess-ai-1/messages", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.route("**/api/v1/swaps/sessions/sess-ai-1/reviews", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.route("**/api/v1/swaps/sessions/sess-ai-1/ai-plan", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          objective: "Master Python async FastAPI dependencies and testing in 30 minutes",
          agenda_items: [
            { minute: "0-5", title: "Warm-up & Scope Alignment", description: "Review goals and environment" },
            { minute: "5-20", title: "Core Walkthrough", description: "Demonstrate AsyncSession and Depends" },
            { minute: "20-27", title: "Hands-on Practice", description: "Learner writes integration test" },
            { minute: "27-30", title: "Wrap-up & Resources", description: "Review key takeaways" },
          ],
          suggested_questions: ["How do we mock dependencies?", "What is the role of commit vs flush?"],
          mentor_tips: "Focus on live examples and give constructive feedback.",
        }),
      });
    });

    await page.route("**/api/v1/swaps/sessions/sess-ai-1/ai-recap", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          summary: "Covered FastAPI async dependency injection, fixture overriding in pytest, and clean database isolation.",
          key_takeaways: [
            "Use AsyncSession in context managers for transactional safety.",
            "Override get_db fixture in test harnesses for isolated in-memory DB.",
          ],
          action_items: [
            "Refactor routes to use Annotated[AsyncSession, Depends(get_db)].",
            "Run full pytest test suite.",
          ],
          recommended_followup: "Explore Alembic async migration patterns.",
        }),
      });
    });
  });

  test("1. Admin Swaps Console: Overview KPIs and Listings Management", async ({ page }) => {
    await page.goto("http://localhost:3000/admin/swaps");

    // Check header
    await expect(page.getByRole("heading", { name: "Skill Swap Economy Console" })).toBeVisible();

    // Verify KPI cards
    await expect(page.getByText("Active Listings")).toBeVisible();
    await expect(page.getByText("18")).toBeVisible();
    await expect(page.getByText("Weekly Swaps")).toBeVisible();
    await expect(page.getByText("12", { exact: true })).toBeVisible();
    await expect(page.getByText("Completion Rate")).toBeVisible();
    await expect(page.getByText("90.5%")).toBeVisible();

    // Verify Top Skills
    await expect(page.getByText("Top Traded Skills")).toBeVisible();
    await expect(page.getByText("Python Backend Development")).toBeVisible();

    // Take screenshot of Admin Overview
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage4_admin_swaps_console.png"),
      fullPage: true,
    });

    // Switch to Listings tab
    await page.getByRole("tab", { name: "Listings" }).click();
    await expect(page.getByText("Swap Listings Directory")).toBeVisible();
    await expect(page.getByText("Suspicious Commercial Tutor Advertising")).toBeVisible();
    await expect(page.getByText("3 reports")).toBeVisible();
  });

  test("2. Admin Swaps Console: Taxonomy Curation and Approval", async ({ page }) => {
    await page.goto("http://localhost:3000/admin/swaps");

    // Click Taxonomy tab
    await page.getByRole("tab", { name: "Taxonomy" }).click();
    await expect(page.getByText("Skill Taxonomy Curation")).toBeVisible();
    await expect(page.getByText("Quantum Computing & Qiskit")).toBeVisible();
    await expect(page.getByRole("button", { name: "Approve" })).toBeVisible();

    // Take screenshot of Taxonomy Curation
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage4_admin_taxonomy_curation.png"),
      fullPage: true,
    });
  });

  test("3. Interactive Session Room: AI Session Planner Modal", async ({ page }) => {
    await page.goto("http://localhost:3000/swaps/sessions/sess-ai-1");

    // Verify AI buttons in action bar
    await expect(page.getByRole("button", { name: "AI Plan" })).toBeVisible();
    await expect(page.getByRole("button", { name: "AI Recap" })).toBeVisible();

    // Open AI Session Planner
    await page.getByRole("button", { name: "AI Plan" }).click();
    await expect(page.getByRole("heading", { name: "Gemini AI Session Planner" })).toBeVisible();

    // Trigger plan generation
    await page.getByRole("button", { name: "Generate 30-Min Agenda" }).click();
    await expect(page.getByText("30-Minute Breakdown:")).toBeVisible();
    await expect(page.getByText("Warm-up & Scope Alignment")).toBeVisible();

    // Take screenshot of AI Planner
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage4_ai_session_planner.png"),
    });
  });

  test("4. Interactive Session Room: AI Post-Session Recap Modal", async ({ page }) => {
    await page.goto("http://localhost:3000/swaps/sessions/sess-ai-1");

    // Open AI Recap
    await page.getByRole("button", { name: "AI Recap" }).click();
    await expect(page.getByRole("heading", { name: "Gemini AI Post-Session Recap" })).toBeVisible();

    // Enter rough notes and generate
    await page
      .getByPlaceholder("Paste key concepts discussed, code snippets, book recommendations...")
      .fill("Covered FastAPI dependency injection, fixtures, and database transactions.");

    await page.getByRole("button", { name: "Generate Takeaways & Action Items" }).click();
    await expect(page.getByText("Key Takeaways:")).toBeVisible();
    await expect(page.getByText("Action Items:")).toBeVisible();

    // Take screenshot of AI Recap
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage4_ai_session_recap.png"),
    });
  });
});
