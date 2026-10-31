/**
 * Skill Swap Frontend API Service
 */

import { apiClient } from "@/lib/api-client";
import {
  GeocodeSearchResult,
  ListingAIDraftRequest,
  ListingAIDraftResponse,
  Skill,
  SkillCategoryGroup,
  SwapDisputeCreate,
  SwapListing,
  SwapListingCreate,
  SwapListingListResponse,
  SwapListingShareResponse,
  SwapListingUpdate,
  SwapMatchResponse,
  SwapMessage,
  SwapRequest,
  SwapRequestAccept,
  SwapRequestCounter,
  SwapRequestCreate,
  SwapRequestListResponse,
  SwapReview,
  SwapReviewCreate,
  SwapSession,
  UserSwapProfilePrivate,
  UserSwapProfilePublic,
} from "@/types/swap";

export const swapApi = {
  getTaxonomy: async (): Promise<SkillCategoryGroup[]> => {
    return apiClient.get<SkillCategoryGroup[]>("/swaps/taxonomy");
  },

  suggestSkill: async (name: string, category: string): Promise<Skill> => {
    return apiClient.post<Skill>("/swaps/taxonomy/suggest", { name, category });
  },

  geocodeLocation: async (query: string): Promise<GeocodeSearchResult[]> => {
    return apiClient.get<GeocodeSearchResult[]>(
      `/swaps/geocode?q=${encodeURIComponent(query)}`
    );
  },

  getMyProfile: async (): Promise<UserSwapProfilePrivate> => {
    return apiClient.get<UserSwapProfilePrivate>("/swaps/profile/me");
  },

  updateMyProfile: async (
    data: Partial<UserSwapProfilePrivate>
  ): Promise<UserSwapProfilePrivate> => {
    return apiClient.put<UserSwapProfilePrivate>("/swaps/profile/me", data);
  },

  getPublicProfile: async (username: string): Promise<UserSwapProfilePublic> => {
    return apiClient.get<UserSwapProfilePublic>(`/swaps/profile/${username}`);
  },

  // ── Listings & Discovery ───────────────────────────────────────────
  createListing: async (data: SwapListingCreate): Promise<SwapListing> => {
    return apiClient.post<SwapListing>("/swaps/listings", data);
  },

  searchListings: async (params?: {
    q?: string;
    category?: string;
    mode?: string;
    distance_bucket?: string;
    sort?: "newest" | "nearest" | "trust";
    limit?: number;
    cursor?: number;
  }): Promise<SwapListingListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.q) searchParams.set("q", params.q);
    if (params?.category) searchParams.set("category", params.category);
    if (params?.mode) searchParams.set("mode", params.mode);
    if (params?.distance_bucket) searchParams.set("distance_bucket", params.distance_bucket);
    if (params?.sort) searchParams.set("sort", params.sort);
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.cursor !== undefined) searchParams.set("cursor", params.cursor.toString());
    const query = searchParams.toString();
    return apiClient.get<SwapListingListResponse>(`/swaps/listings${query ? `?${query}` : ""}`);
  },

  getMyListings: async (): Promise<SwapListing[]> => {
    return apiClient.get<SwapListing[]>("/swaps/listings/me");
  },

  getListingById: async (listingId: string): Promise<SwapListing> => {
    return apiClient.get<SwapListing>(`/swaps/listings/${listingId}`);
  },

  updateListing: async (listingId: string, data: SwapListingUpdate): Promise<SwapListing> => {
    return apiClient.put<SwapListing>(`/swaps/listings/${listingId}`, data);
  },

  shareListingToFeed: async (listingId: string): Promise<SwapListingShareResponse> => {
    return apiClient.post<SwapListingShareResponse>(`/swaps/listings/${listingId}/share`, {});
  },

  generateAIDraft: async (data: ListingAIDraftRequest): Promise<ListingAIDraftResponse> => {
    return apiClient.post<ListingAIDraftResponse>("/swaps/listings/ai-draft", data);
  },

  getMatches: async (limit: number = 10): Promise<SwapMatchResponse[]> => {
    return apiClient.get<SwapMatchResponse[]>(`/swaps/matches?limit=${limit}`);
  },

  // ── Stage 3: Requests & Proposals ──────────────────────────────────
  createRequest: async (data: SwapRequestCreate): Promise<SwapRequest> => {
    return apiClient.post<SwapRequest>("/swaps/requests", data);
  },

  getRequests: async (): Promise<SwapRequestListResponse> => {
    return apiClient.get<SwapRequestListResponse>("/swaps/requests");
  },

  getRequestById: async (id: string): Promise<SwapRequest> => {
    return apiClient.get<SwapRequest>(`/swaps/requests/${id}`);
  },

  acceptRequest: async (id: string, payload: SwapRequestAccept): Promise<SwapSession> => {
    return apiClient.post<SwapSession>(`/swaps/requests/${id}/accept`, payload);
  },

  counterRequest: async (id: string, payload: SwapRequestCounter): Promise<SwapRequest> => {
    return apiClient.post<SwapRequest>(`/swaps/requests/${id}/counter`, payload);
  },

  declineRequest: async (id: string): Promise<SwapRequest> => {
    return apiClient.post<SwapRequest>(`/swaps/requests/${id}/decline`, {});
  },

  cancelRequest: async (id: string): Promise<SwapRequest> => {
    return apiClient.post<SwapRequest>(`/swaps/requests/${id}/cancel`, {});
  },

  // ── Stage 3: Sessions, Logistics & Reviews ─────────────────────────
  getMySessions: async (): Promise<SwapSession[]> => {
    return apiClient.get<SwapSession[]>("/swaps/sessions/me");
  },

  getSessionById: async (id: string): Promise<SwapSession> => {
    return apiClient.get<SwapSession>(`/swaps/sessions/${id}`);
  },

  confirmSession: async (id: string): Promise<SwapSession> => {
    return apiClient.post<SwapSession>(`/swaps/sessions/${id}/confirm`, {});
  },

  disputeSession: async (id: string, data: SwapDisputeCreate): Promise<SwapSession> => {
    return apiClient.post<SwapSession>(`/swaps/sessions/${id}/dispute`, data);
  },

  getSessionMessages: async (id: string): Promise<SwapMessage[]> => {
    return apiClient.get<SwapMessage[]>(`/swaps/sessions/${id}/messages`);
  },

  postSessionMessage: async (id: string, content: string): Promise<SwapMessage> => {
    return apiClient.post<SwapMessage>(`/swaps/sessions/${id}/messages`, { content });
  },

  getSessionReviews: async (id: string): Promise<SwapReview[]> => {
    return apiClient.get<SwapReview[]>(`/swaps/sessions/${id}/reviews`);
  },

  submitSessionReview: async (id: string, data: SwapReviewCreate): Promise<SwapReview> => {
    return apiClient.post<SwapReview>(`/swaps/sessions/${id}/reviews`, data);
  },
};


