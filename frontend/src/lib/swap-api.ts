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
  SwapListing,
  SwapListingCreate,
  SwapListingListResponse,
  SwapListingShareResponse,
  SwapListingUpdate,
  SwapMatchResponse,
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
};

