# Chapter 24: Skill Swap API Reference & Data Architecture

## 1. Complete REST API Reference (`/api/v1/swaps`)

All endpoints use standardized JSON responses, consistent error schemas (`400`, `401`, `403`, `404`, `422`), and require Bearer JWT authentication unless marked Public.

### 1.1 Skill Taxonomy & Normalization

| Method | Endpoint | Auth | Request Body | Response Model | Description |
|---|---|---|---|---|---|
| `GET` | `/taxonomy` | None | Query params: `category`, `search` | `SkillListResponse` | List canonical skills and active categories |
| `POST` | `/taxonomy/suggest` | User | `SkillCreateRequest` | `SkillResponse` | Suggest new skill (auto-approved or queued) |

### 1.2 User Swap Profiles & Location Privacy

| Method | Endpoint | Auth | Request Body | Response Model | Description |
|---|---|---|---|---|---|
| `GET` | `/profile/me` | User | None | `UserSwapProfileResponse` | Retrieve own swap settings, availability & coords |
| `PUT` | `/profile/me` | User | `UserSwapProfileUpdate` | `UserSwapProfileResponse` | Update skills, availability windows & coarse area |
| `GET` | `/profile/{username}` | User | None | `UserSwapProfilePublicResponse` | View public profile with **distance bucket only** |

### 1.3 Swap Listings (Offers)

| Method | Endpoint | Auth | Request Body | Response Model | Description |
|---|---|---|---|---|---|
| `POST` | `/listings` | User | `SwapListingCreate` | `SwapListingResponse` | Create new listing with anti-money validation |
| `GET` | `/listings` | User | Query params: `mode`, `distance`, `category`, `sort`, `cursor` | `SwapListingListResponse` | Spatial discovery search with distance buckets |
| `GET` | `/listings/me` | User | None | `list[SwapListingResponse]` | Retrieve own published listings |
| `GET` | `/listings/{id}` | User | None | `SwapListingResponse` | Retrieve listing details |
| `PUT` | `/listings/{id}` | User | `SwapListingUpdate` | `SwapListingResponse` | Edit or change status (`active`, `paused`, `closed`) |
| `POST` | `/listings/{id}/share` | User | None | `SwapListingShareResponse` | Share listing into social feed as Swap Post |

### 1.4 Recommendations & Matching

| Method | Endpoint | Auth | Request Body | Response Model | Description |
|---|---|---|---|---|---|
| `GET` | `/matches` | User | Query params: `limit` | `SwapMatchListResponse` | 5-criteria weighted matches with cached AI reasons |

### 1.5 Swap Proposals & Negotiation Lifecycle

| Method | Endpoint | Auth | Request Body | Response Model | Description |
|---|---|---|---|---|---|
| `POST` | `/requests` | User | `SwapRequestCreate` | `SwapRequestResponse` | Propose swap with up to 3 candidate slots |
| `GET` | `/requests` | User | Query params: `status`, `direction` | `SwapRequestListResponse` | Retrieve incoming & outgoing proposals |
| `POST` | `/requests/{id}/accept` | User | `SwapRequestAccept` | `SwapSessionResponse` | Accept request & auto-create 2-half session |
| `POST` | `/requests/{id}/counter` | User | `SwapRequestCounter` | `SwapRequestResponse` | Counter-propose alternate slots or mode |
| `POST` | `/requests/{id}/decline` | User | None | `SwapRequestResponse` | Decline swap proposal |
| `POST` | `/requests/{id}/cancel` | User | None | `SwapRequestResponse` | Cancel outgoing proposal |

### 1.6 Sessions, Halves & Video Logistics

| Method | Endpoint | Auth | Request Body | Response Model | Description |
|---|---|---|---|---|---|
| `GET` | `/sessions/{id}` | Participant | None | `SwapSessionResponse` | Get session details, halves, and Jitsi link |
| `GET` | `/sessions/{id}/ics` | Participant | None | Binary `.ics` | Download RFC 5545 calendar invite |
| `POST` | `/sessions/{id}/complete` | Participant | `SwapSessionConfirm` | `SwapSessionResponse` | Confirm completion of mentored/learned half |
| `POST` | `/sessions/{id}/dispute` | Participant | `SwapSessionDispute` | `SwapSessionResponse` | Flag session for dispute or no-show triage |
| `GET` | `/sessions/{id}/messages` | Participant | None | `list[SwapMessageResponse]` | Retrieve session logistics chat messages |
| `POST` | `/sessions/{id}/messages` | Participant | `SwapMessageCreate` | `SwapMessageResponse` | Post message (broadcast via SSE channel) |

### 1.7 Double-Blind Reviews & Trust

| Method | Endpoint | Auth | Request Body | Response Model | Description |
|---|---|---|---|---|---|
| `POST` | `/reviews` | Participant | `SwapReviewCreate` | `SwapReviewResponse` | Submit blind review (rating, tags, notes) |
| `GET` | `/sessions/{id}/reviews`| Participant | None | `list[SwapReviewResponse]` | Get session reviews (hidden until revealed) |
| `GET` | `/trust/{user_id}` | User | None | `TrustScoreResponse` | Get user trust score, completed count & badges |

### 1.8 Gemini AI Assistants

| Method | Endpoint | Auth | Request Body | Response Model | Description |
|---|---|---|---|---|---|
| `POST` | `/sessions/{id}/ai-plan` | Participant | `SwapSessionPlanRequest` | `SwapSessionPlanResponse` | Generate structured 30-minute agenda |
| `POST` | `/sessions/{id}/ai-recap` | Participant | `SwapSessionRecapRequest` | `SwapSessionRecapResponse` | Convert session notes into action takeaways |
| `GET` | `/fairness-advice` | User | None | `SwapFairnessAdviceResponse` | Reciprocity ledger balance guidance |

### 1.9 Admin & Internal Maintenance Endpoints

| Method | Endpoint | Auth | Request Body | Description |
|---|---|---|---|---|
| `GET` | `/api/v1/admin/swaps/stats` | Admin | None | Platform-wide KPIs & top traded skills |
| `GET` | `/api/v1/admin/swaps/listings` | Admin | Query params | Manage & suspend/reinstate listings |
| `GET` | `/api/v1/admin/swaps/disputes` | Admin | None | Triage queue of disputes and no-shows |
| `POST` | `/api/v1/admin/swaps/disputes/{id}/resolve` | Admin | `SwapDisputeResolveRequest` | Resolve dispute & adjust trust scores |
| `POST` | `/api/v1/admin/swaps/taxonomy/approve` | Admin | `SkillApproveRequest` | Approve pending user-suggested skills |
| `POST` | `/api/v1/admin/swaps/taxonomy/merge` | Admin | `SkillMergeRequest` | Merge skill synonyms into canonical slug |
| `POST` | `/api/v1/internal/jobs/{job_name}` | `X-Cron-Secret` | None | Execute scheduled maintenance tasks |

---

## 2. Complete 17-Table Data Architecture

Alembic migration `0004_add_skill_swap_economy.py` defines the 17 domain tables with UUID primary keys and cascading foreign keys:

1. `skills`: Canonical taxonomy catalog with slugs, categories, and alias arrays.
2. `user_skills`: User-declared teaching and learning capabilities (`level`, `years_experience`, `notes`).
3. `user_swap_profiles`: Privacy-coarsened location (`coarse_lat`, `coarse_lng`), `area_label`, `radius_km`, modes, and 18+ confirmation.
4. `availability_windows`: Recurring weekly UTC intervals (0=Monday to 6=Sunday).
5. `availability_blackouts`: One-off UTC unavailable intervals with reasons.
6. `swap_listings`: Published swap offers (`status = active | paused | closed | removed`).
7. `swap_requests`: Negotiation state machine records with proposed slot intervals.
8. `swap_sessions`: Agreed 60-minute exchanges linked to Jitsi room tokens and public places.
9. `swap_session_halves`: Two fixed 30-minute halves per session (Half 1 and Half 2).
10. `swap_messages`: Session-scoped real-time logistics chat.
11. `swap_reviews`: Double-blind ratings, behavioral tags, and feedback (`is_revealed = False` initially).
12. `user_blocks`: Bi-directional blocking records.
13. `swap_reports`: Safety and behavioral reports with 3-strike aggregation.
14. `trust_scores`: Bayesian trust scores (0–100), completed sessions, no-show penalties, and badges.
15. `reciprocity_ledger`: Minutes taught vs. learned balance with -60 minute grace window.
16. `match_explanations`: SHA-256 hashed cache of Gemini match explanations.
17. `job_runs`: Audit logging of Render Cron job executions.
