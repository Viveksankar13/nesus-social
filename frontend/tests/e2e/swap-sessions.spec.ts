import { test, expect } from "@playwright/test";
import path from "path";

const SCREENSHOT_DIR =
  "C:/Users/BRENWEN/.gemini/antigravity/brain/ef3e3560-ae99-4f2b-a134-74e48999f2c5/screenshots";

const MOCK_PROPOSAL = {
  id: "req-123",
  listing_id: "list-123",
  requester: {
    id: "user-1",
    username: "alex_coder",
    display_name: "Alex Rivera",
    avatar_url: null,
    usn: "1MS21CS042",
  },
  recipient: {
    id: "user-2",
    username: "sophia_tech",
    display_name: "Sophia Chen",
    avatar_url: null,
    usn: "1MS21CS098",
  },
  offered_skill: {
    id: "skill-1",
    slug: "algorithms-ds",
    display_name: "Algorithms & Data Structures",
    category: "Technology",
    aliases: ["dsa"],
    status: "active",
    created_at: new Date().toISOString(),
  },
  wanted_skill: {
    id: "skill-2",
    slug: "conversational-french",
    display_name: "Conversational French",
    category: "Languages",
    aliases: ["french"],
    status: "active",
    created_at: new Date().toISOString(),
  },
  mode: "video",
  message:
    "Hi Sophia! I would love to explain dynamic programming and graph traversals in return for practicing conversational French dialogue.",
  proposed_slots: [
    {
      start_time_utc: new Date(Date.now() + 86400000).toISOString(),
      end_time_utc: new Date(Date.now() + 86400000 + 1800000).toISOString(),
    },
    {
      start_time_utc: new Date(Date.now() + 172800000).toISOString(),
      end_time_utc: new Date(Date.now() + 172800000 + 1800000).toISOString(),
    },
  ],
  status: "pending",
  counter_note: null,
  expires_at: new Date(Date.now() + 259200000).toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const MOCK_SESSION = {
  id: "sess-456",
  request_id: "req-123",
  user_a: {
    id: "user-1",
    username: "alex_coder",
    display_name: "Alex Rivera",
    avatar_url: null,
    usn: "1MS21CS042",
  },
  user_b: {
    id: "user-2",
    username: "sophia_tech",
    display_name: "Sophia Chen",
    avatar_url: null,
    usn: "1MS21CS098",
  },
  status: "scheduled",
  mode: "video",
  public_place_name: null,
  public_place_address: null,
  jitsi_room_token: "unguessable-token-789",
  jitsi_room_url: "https://meet.jit.si/nexus-swap-sess-456-unguessable-token-789",
  user_a_confirmed: false,
  user_b_confirmed: false,
  dispute_reason: null,
  halves: [
    {
      id: "half-1",
      session_id: "sess-456",
      half_number: 1,
      mentor: {
        id: "user-1",
        username: "alex_coder",
        display_name: "Alex Rivera",
        avatar_url: null,
        usn: "1MS21CS042",
      },
      learner: {
        id: "user-2",
        username: "sophia_tech",
        display_name: "Sophia Chen",
        avatar_url: null,
        usn: "1MS21CS098",
      },
      skill: {
        id: "skill-1",
        slug: "algorithms-ds",
        display_name: "Algorithms & Data Structures",
        category: "Technology",
        aliases: ["dsa"],
        status: "active",
        created_at: new Date().toISOString(),
      },
      start_time_utc: new Date(Date.now() + 3600000).toISOString(),
      end_time_utc: new Date(Date.now() + 5400000).toISOString(),
      status: "scheduled",
      ics_uid: "half1@nexussocial.dev",
    },
    {
      id: "half-2",
      session_id: "sess-456",
      half_number: 2,
      mentor: {
        id: "user-2",
        username: "sophia_tech",
        display_name: "Sophia Chen",
        avatar_url: null,
        usn: "1MS21CS098",
      },
      learner: {
        id: "user-1",
        username: "alex_coder",
        display_name: "Alex Rivera",
        avatar_url: null,
        usn: "1MS21CS042",
      },
      skill: {
        id: "skill-2",
        slug: "conversational-french",
        display_name: "Conversational French",
        category: "Languages",
        aliases: ["french"],
        status: "active",
        created_at: new Date().toISOString(),
      },
      start_time_utc: new Date(Date.now() + 5400000).toISOString(),
      end_time_utc: new Date(Date.now() + 7200000).toISOString(),
      status: "scheduled",
      ics_uid: "half2@nexussocial.dev",
    },
  ],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

test.describe("Skill Swap Economy — Stage 3 Requests & Sessions", () => {
  test("Proposals Inbox page renders populated proposal cards and action buttons", async ({
    page,
  }) => {
    // Intercept proposals API
    await page.route("**/api/v1/swaps/requests", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          incoming: [MOCK_PROPOSAL],
          outgoing: [],
        }),
      });
    });

    await page.goto("/swaps/requests");

    // Verify heading and proposal cards
    await expect(page.getByRole("heading", { name: /Proposals Inbox/i })).toBeVisible();
    await expect(page.locator("text=Alex Rivera")).toBeVisible();
    await expect(page.locator("text=Algorithms & Data Structures").first()).toBeVisible();
    await expect(page.locator("text=Conversational French").first()).toBeVisible();
    await expect(page.getByRole("button", { name: /Accept & Schedule/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Counter-Offer/i })).toBeVisible();

    // Screenshot populated inbox
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage3_proposals_inbox.png"),
      fullPage: true,
    });
  });

  test("My Sessions page renders upcoming scheduled cards with halves timeline", async ({
    page,
  }) => {
    // Intercept sessions API
    await page.route("**/api/v1/swaps/sessions/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([MOCK_SESSION]),
      });
    });

    await page.goto("/swaps/sessions");

    // Verify session card
    await expect(page.getByRole("heading", { name: /My Swap Sessions/i })).toBeVisible();
    await expect(page.locator("text=Swap with @sophia_tech")).toBeVisible();
    await expect(page.locator("text=Half 1 (30m)").first()).toBeVisible();
    await expect(page.locator("text=Half 2 (30m)").first()).toBeVisible();

    // Screenshot populated sessions page
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage3_sessions_calendar.png"),
      fullPage: true,
    });
  });

  test("Interactive Session Room renders split halves, Jitsi room, and logistics chat", async ({
    page,
  }) => {
    // Intercept session and messages API
    await page.route("**/api/v1/swaps/sessions/sess-456", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_SESSION),
      });
    });

    await page.route("**/api/v1/swaps/sessions/sess-456/messages", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "msg-1",
            session_id: "sess-456",
            sender: {
              id: "user-2",
              username: "sophia_tech",
              display_name: "Sophia Chen",
              avatar_url: null,
            },
            content: "Bonjour Alex! Ready to swap algorithms and French?",
            created_at: new Date(Date.now() - 600000).toISOString(),
          },
          {
            id: "msg-2",
            session_id: "sess-456",
            sender: {
              id: "user-1",
              username: "alex_coder",
              display_name: "Alex Rivera",
              avatar_url: null,
            },
            content: "Hey Sophia, absolutely! I have my code editor and microphone ready.",
            created_at: new Date(Date.now() - 300000).toISOString(),
          },
        ]),
      });
    });

    await page.route("**/api/v1/swaps/sessions/sess-456/reviews", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/swaps/sessions/sess-456");

    // Verify room elements
    await expect(page.locator("text=Skill Swap Session Room")).toBeVisible();
    await expect(page.locator("text=Half 1 (30 Minutes)")).toBeVisible();
    await expect(page.locator("text=Half 2 (30 Minutes)")).toBeVisible();
    await expect(page.locator("text=Live Video Room (Jitsi Meet)")).toBeVisible();
    await expect(page.locator("text=Session Logistics Chat")).toBeVisible();
    await expect(page.locator("text=Bonjour Alex!")).toBeVisible();

    // Screenshot interactive session room
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage3_interactive_session_room.png"),
      fullPage: true,
    });
  });

  test("Proposal Modal opens with Slot Picker and public place safety guidance", async ({
    page,
  }) => {
    // Intercept listing
    await page.route("**/api/v1/swaps/listings/demo-listing", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "demo-listing",
          user_id: "user-2",
          user: {
            id: "user-2",
            username: "sophia_tech",
            display_name: "Sophia Chen",
            avatar_url: null,
            usn: "1MS21CS098",
          },
          title: "Conversational French for DSA Help",
          skill_offered: {
            id: "skill-2",
            slug: "conversational-french",
            display_name: "Conversational French",
            category: "Languages",
            aliases: ["french"],
            status: "active",
            created_at: new Date().toISOString(),
          },
          skill_wanted: {
            id: "skill-1",
            slug: "algorithms-ds",
            display_name: "Algorithms & Data Structures",
            category: "Technology",
            aliases: ["dsa"],
            status: "active",
            created_at: new Date().toISOString(),
          },
          description: "Offering 30 minutes of French dialogue practice in exchange for algorithms mentoring.",
          modes: ["video", "in_person"],
          area_label: "North Campus",
          status: "active",
          tags: ["french", "dsa"],
          distance_bucket: "1–3 km",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto("/swaps/demo-listing");

    const proposeBtn = page.getByRole("button", { name: /Propose a 30-Min Swap/i });
    await expect(proposeBtn).toBeVisible();
    await proposeBtn.click();

    // Check modal visibility
    await expect(page.locator("text=Propose a Skill Swap")).toBeVisible();
    await expect(page.locator("text=Proposed 30-Minute Time Slots")).toBeVisible();
    await expect(page.locator("text=Remote Jitsi Video")).toBeVisible();

    // Screenshot propose modal
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "stage3_propose_swap_modal.png"),
    });
  });
});
