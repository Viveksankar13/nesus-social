/**
 * Skill Swap TypeScript Types & Interfaces
 */

export interface Skill {
  id: string;
  slug: string;
  display_name: string;
  category: string;
  aliases: string[];
  status: "active" | "pending" | "rejected";
  created_at: string;
}

export interface SkillCategoryGroup {
  category: string;
  skills: Skill[];
}

export interface UserSkill {
  id?: string;
  skill_slug: string;
  skill?: Skill;
  skill_type: "teach" | "learn";
  level: "beginner" | "intermediate" | "advanced" | "expert";
  years_experience?: number | null;
  notes?: string | null;
}

export interface AvailabilityWindow {
  id?: string;
  day_of_week: number; // 0=Monday ... 6=Sunday
  start_time_utc: string; // "HH:MM"
  end_time_utc: string; // "HH:MM"
}

export interface AvailabilityBlackout {
  id?: string;
  start_datetime_utc: string;
  end_datetime_utc: string;
  reason?: string | null;
}

export interface GeocodeSearchResult {
  name: string;
  area_label: string;
  coarse_lat: number;
  coarse_lng: number;
  country?: string | null;
  admin1?: string | null;
}

export interface UserSwapProfilePrivate {
  user_id: string;
  bio: string | null;
  coarse_lat: number | null;
  coarse_lng: number | null;
  area_label: string | null;
  radius_km: number;
  modes: string[];
  languages: string[];
  is_invisible: boolean;
  accepts_newcomers: boolean;
  is_18_confirmed: boolean;

  teach_skills: UserSkill[];
  learn_skills: UserSkill[];
  availability_windows: AvailabilityWindow[];
  blackout_dates: AvailabilityBlackout[];

  trust_score: number;
  avg_rating: number;
  completed_swaps: number;
  badges: string[];
  reciprocity_balance_minutes: number;
}

export interface PublicUserMinimal {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  usn?: string | null;
}

export interface UserSwapProfilePublic {
  user: PublicUserMinimal;
  bio: string | null;
  area_label: string | null;
  distance_bucket: string; // "under 1 km", "1–3 km", "3–5 km", "5–10 km", "10–25 km", or "remote"
  modes: string[];
  languages: string[];
  accepts_newcomers: boolean;

  teach_skills: UserSkill[];
  learn_skills: UserSkill[];

  trust_score: number;
  avg_rating: number;
  completed_swaps: number;
  badges: string[];
}
