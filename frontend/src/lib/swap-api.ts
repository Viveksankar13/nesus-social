/**
 * Skill Swap Frontend API Service
 */

import { apiClient } from "@/lib/api-client";
import {
  GeocodeSearchResult,
  Skill,
  SkillCategoryGroup,
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
};
