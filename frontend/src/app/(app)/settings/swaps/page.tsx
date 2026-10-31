"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar,
  Check,
  Compass,
  GraduationCap,
  MapPin,
  Plus,
  Repeat,
  Save,
  Search,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { swapApi } from "@/lib/swap-api";
import {
  AvailabilityWindow,
  GeocodeSearchResult,
  Skill,
  UserSkill,
} from "@/types/swap";

const DAYS_OF_WEEK = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export default function SwapSettingsPage() {
  const queryClient = useQueryClient();

  const [bio, setBio] = React.useState("");
  const [teachSkills, setTeachSkills] = React.useState<UserSkill[]>([]);
  const [learnSkills, setLearnSkills] = React.useState<UserSkill[]>([]);
  const [availabilityWindows, setAvailabilityWindows] = React.useState<
    AvailabilityWindow[]
  >([]);
  const [areaLabel, setAreaLabel] = React.useState("");
  const [coarseLat, setCoarseLat] = React.useState<number | null>(null);
  const [coarseLng, setCoarseLng] = React.useState<number | null>(null);
  const [radiusKm, setRadiusKm] = React.useState<number>(10);
  const [modes, setModes] = React.useState<string[]>(["video", "in_person"]);
  const [isInvisible, setIsInvisible] = React.useState<boolean>(false);
  const [acceptsNewcomers, setAcceptsNewcomers] = React.useState<boolean>(true);
  const [is18Confirmed, setIs18Confirmed] = React.useState<boolean>(false);

  // Skill Search State
  const [skillSearch, setSkillSearch] = React.useState("");
  const [selectedCategory, setSelectedCategory] = React.useState<string>("All");
  const [activeSkillTab, setActiveSkillTab] = React.useState<"teach" | "learn">(
    "teach"
  );
  const [saveSuccess, setSaveSuccess] = React.useState(false);

  // Geocode Search State
  const [geoQuery, setGeoQuery] = React.useState("");
  const [geoResults, setGeoResults] = React.useState<GeocodeSearchResult[]>([]);

  // Fetch Own Profile
  const { data: profile, isLoading } = useQuery({
    queryKey: ["swap-profile", "me"],
    queryFn: swapApi.getMyProfile,
  });

  // Fetch Taxonomy
  const { data: taxonomy = [] } = useQuery({
    queryKey: ["swap-taxonomy"],
    queryFn: swapApi.getTaxonomy,
  });

  // Initialize
  React.useEffect(() => {
    if (profile) {
      setBio(profile.bio || "");
      setTeachSkills(profile.teach_skills || []);
      setLearnSkills(profile.learn_skills || []);
      setAvailabilityWindows(profile.availability_windows || []);
      setAreaLabel(profile.area_label || "");
      setCoarseLat(profile.coarse_lat);
      setCoarseLng(profile.coarse_lng);
      setRadiusKm(profile.radius_km);
      setModes(profile.modes || ["video", "in_person"]);
      setIsInvisible(profile.is_invisible);
      setAcceptsNewcomers(profile.accepts_newcomers);
      setIs18Confirmed(profile.is_18_confirmed);
    }
  }, [profile]);

  // Geocode Search Debounced
  React.useEffect(() => {
    if (geoQuery.trim().length < 2) {
      setGeoResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await swapApi.geocodeLocation(geoQuery);
        setGeoResults(res);
      } catch {
        setGeoResults([]);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [geoQuery]);

  // Save Mutation
  const saveMutation = useMutation({
    mutationFn: () =>
      swapApi.updateMyProfile({
        bio,
        teach_skills: teachSkills,
        learn_skills: learnSkills,
        availability_windows: availabilityWindows,
        area_label: areaLabel || "Remote Only",
        coarse_lat: coarseLat,
        coarse_lng: coarseLng,
        radius_km: radiusKm,
        modes,
        is_invisible: isInvisible,
        accepts_newcomers: acceptsNewcomers,
        is_18_confirmed: is18Confirmed,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["swap-profile"] });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    },
  });

  // Skills Filter
  const allSkills = React.useMemo(() => {
    const list: Skill[] = [];
    taxonomy.forEach((g) => {
      if (selectedCategory === "All" || selectedCategory === g.category) {
        list.push(...g.skills);
      }
    });
    if (!skillSearch.trim()) return list;
    const q = skillSearch.toLowerCase();
    return list.filter(
      (s) =>
        s.display_name.toLowerCase().includes(q) ||
        s.slug.toLowerCase().includes(q) ||
        s.aliases.some((a) => a.toLowerCase().includes(q))
    );
  }, [taxonomy, selectedCategory, skillSearch]);

  const handleAddSkill = (slug: string, displayName: string) => {
    if (activeSkillTab === "teach") {
      if (teachSkills.some((s) => s.skill_slug === slug)) return;
      setTeachSkills([
        ...teachSkills,
        {
          skill_slug: slug,
          skill_type: "teach",
          level: "intermediate",
          years_experience: 1,
          notes: `Experienced in ${displayName}.`,
        },
      ]);
    } else {
      if (learnSkills.some((s) => s.skill_slug === slug)) return;
      setLearnSkills([
        ...learnSkills,
        {
          skill_slug: slug,
          skill_type: "learn",
          level: "beginner",
          years_experience: 0,
          notes: `Interested in learning ${displayName}.`,
        },
      ]);
    }
  };

  const handleToggleDay = (dayIndex: number) => {
    const exists = availabilityWindows.some((w) => w.day_of_week === dayIndex);
    if (exists) {
      setAvailabilityWindows(
        availabilityWindows.filter((w) => w.day_of_week !== dayIndex)
      );
    } else {
      setAvailabilityWindows([
        ...availabilityWindows,
        {
          day_of_week: dayIndex,
          start_time_utc: "09:00",
          end_time_utc: "17:00",
        },
      ]);
    }
  };

  const handleUpdateTime = (
    dayIndex: number,
    field: "start_time_utc" | "end_time_utc",
    val: string
  ) => {
    setAvailabilityWindows(
      availabilityWindows.map((w) =>
        w.day_of_week === dayIndex ? { ...w, [field]: val } : w
      )
    );
  };

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-2">
            <Repeat className="h-3.5 w-3.5" />
            <span>Skill Swap Settings</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            Preferences & Competencies
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your skill offerings, learning wishlist, recurring calendar, and privacy.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {saveSuccess && (
            <span className="text-xs text-green-600 font-semibold flex items-center gap-1">
              <Check className="h-3.5 w-3.5" /> Saved!
            </span>
          )}
          <Button
            size="sm"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="gap-1.5 shadow-sm"
          >
            <Save className="h-4 w-4" />
            <span>{saveMutation.isPending ? "Saving..." : "Save Settings"}</span>
          </Button>
        </div>
      </div>

      {/* Trust & Reciprocity Summary Card */}
      {profile && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-2xl border bg-gradient-to-br from-primary/5 via-card to-card">
          <div className="p-3">
            <p className="text-xs text-muted-foreground uppercase font-semibold">
              Trust Score
            </p>
            <p className="text-2xl font-extrabold text-foreground mt-1">
              {profile.trust_score}
              <span className="text-xs text-muted-foreground font-normal">/100</span>
            </p>
          </div>
          <div className="p-3">
            <p className="text-xs text-muted-foreground uppercase font-semibold">
              Average Rating
            </p>
            <p className="text-2xl font-extrabold text-amber-500 mt-1">
              ★ {profile.avg_rating.toFixed(1)}
            </p>
          </div>
          <div className="p-3">
            <p className="text-xs text-muted-foreground uppercase font-semibold">
              Completed Swaps
            </p>
            <p className="text-2xl font-extrabold text-foreground mt-1">
              {profile.completed_swaps}
            </p>
          </div>
          <div className="p-3">
            <p className="text-xs text-muted-foreground uppercase font-semibold">
              Trade Balance
            </p>
            <p className="text-2xl font-extrabold text-primary mt-1">
              {profile.reciprocity_balance_minutes >= 0 ? "+" : ""}
              {profile.reciprocity_balance_minutes}m
            </p>
          </div>
        </div>
      )}

      {/* ── Section 1: Skills Management ─────────────────────────────── */}
      <div className="space-y-4 p-6 rounded-2xl border bg-card shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-bold">Skills & Competencies</h2>
          </div>
          <div className="flex rounded-lg border p-1 bg-muted/30">
            <button
              type="button"
              onClick={() => setActiveSkillTab("teach")}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeSkillTab === "teach"
                  ? "bg-card text-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              I Can Teach ({teachSkills.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveSkillTab("learn")}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeSkillTab === "learn"
                  ? "bg-card text-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              I Want to Learn ({learnSkills.length})
            </button>
          </div>
        </div>

        {/* Selected List */}
        <div className="space-y-2 pt-2">
          {activeSkillTab === "teach" ? (
            teachSkills.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                No teaching skills added yet. Select topics from the cloud below.
              </p>
            ) : (
              teachSkills.map((ts) => (
                <div
                  key={ts.skill_slug}
                  className="flex items-center justify-between p-3 rounded-xl border bg-accent/20 gap-3"
                >
                  <div className="flex-1">
                    <span className="font-semibold text-sm capitalize">
                      {ts.skill_slug.replace(/-/g, " ")}
                    </span>
                    <span className="text-xs text-muted-foreground ml-2 capitalize">
                      ({ts.level} · {ts.years_experience || 0} yrs)
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setTeachSkills(
                        teachSkills.filter((s) => s.skill_slug !== ts.skill_slug)
                      )
                    }
                    className="text-destructive h-7 w-7 p-0"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))
            )
          ) : learnSkills.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">
              No learning skills added yet. Select topics from the cloud below.
            </p>
          ) : (
            learnSkills.map((ls) => (
              <div
                key={ls.skill_slug}
                className="flex items-center justify-between p-3 rounded-xl border bg-accent/20 gap-3"
              >
                <div className="flex-1">
                  <span className="font-semibold text-sm capitalize">
                    {ls.skill_slug.replace(/-/g, " ")}
                  </span>
                  <span className="text-xs text-muted-foreground ml-2 capitalize">
                    ({ls.level})
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    setLearnSkills(
                      learnSkills.filter((s) => s.skill_slug !== ls.skill_slug)
                    )
                  }
                  className="text-destructive h-7 w-7 p-0"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))
          )}
        </div>

        {/* Add Skills Cloud */}
        <div className="space-y-3 pt-3 border-t">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">
            Add to {activeSkillTab === "teach" ? "Teaching" : "Learning"} Wishlist
          </Label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search skills..."
                value={skillSearch}
                onChange={(e) => setSkillSearch(e.target.value)}
                className="pl-9 h-9 text-xs"
              />
            </div>
            <Select
              value={selectedCategory}
              onValueChange={(v) => setSelectedCategory(v)}
            >
              <SelectTrigger className="w-40 h-9 text-xs">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="All">All</SelectItem>
                {taxonomy.map((c) => (
                  <SelectItem key={c.category} value={c.category}>
                    {c.category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto p-2 rounded-xl border bg-muted/20">
            {allSkills.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => handleAddSkill(s.slug, s.display_name)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-card hover:bg-accent border text-foreground"
              >
                <span>{s.display_name}</span>
                <Plus className="h-3 w-3 opacity-60" />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Section 2: Weekly Availability ───────────────────────────── */}
      <div className="space-y-4 p-6 rounded-2xl border bg-card shadow-sm">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-bold">Weekly Availability (UTC)</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Toggle the days and times you can commit to 30-minute peer swaps.
        </p>

        <div className="grid gap-2 pt-2">
          {DAYS_OF_WEEK.map((dayName, dayIndex) => {
            const w = availabilityWindows.find((x) => x.day_of_week === dayIndex);
            const isEnabled = !!w;

            return (
              <div
                key={dayName}
                className={`flex items-center justify-between p-3 rounded-xl border ${
                  isEnabled ? "bg-accent/30 border-primary/30" : "bg-card opacity-60"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Switch
                    checked={isEnabled}
                    onCheckedChange={() => handleToggleDay(dayIndex)}
                  />
                  <span className="text-xs font-semibold w-24">{dayName}</span>
                </div>

                {isEnabled && (
                  <div className="flex items-center gap-2 text-xs">
                    <Input
                      type="time"
                      value={w?.start_time_utc || "09:00"}
                      onChange={(e) =>
                        handleUpdateTime(dayIndex, "start_time_utc", e.target.value)
                      }
                      className="h-7 w-24 text-xs"
                    />
                    <span className="text-muted-foreground">to</span>
                    <Input
                      type="time"
                      value={w?.end_time_utc || "17:00"}
                      onChange={(e) =>
                        handleUpdateTime(dayIndex, "end_time_utc", e.target.value)
                      }
                      className="h-7 w-24 text-xs"
                    />
                    <span className="text-[10px] text-muted-foreground">UTC</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Section 3: Privacy & Location ────────────────────────────── */}
      <div className="space-y-4 p-6 rounded-2xl border bg-card shadow-sm">
        <div className="flex items-center gap-2">
          <Compass className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-bold">Location & Privacy by Design</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          We protect your exact location. Coarse coordinates (~1 km resolution) are used
          exclusively for distance bucketing.
        </p>

        <div className="space-y-3 pt-2">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">
            Neighborhood / General Area
          </Label>
          <div className="relative">
            <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search city, district, or area..."
              value={geoQuery || areaLabel}
              onChange={(e) => {
                setGeoQuery(e.target.value);
                setAreaLabel(e.target.value);
              }}
              className="pl-9 h-9 text-xs"
            />
          </div>

          {geoResults.length > 0 && (
            <div className="rounded-xl border bg-card p-2 shadow-sm space-y-1">
              {geoResults.map((r, i) => (
                <div
                  key={i}
                  onClick={() => {
                    setAreaLabel(r.area_label);
                    setCoarseLat(r.coarse_lat);
                    setCoarseLng(r.coarse_lng);
                    setGeoQuery(r.area_label);
                    setGeoResults([]);
                  }}
                  className="px-3 py-1.5 rounded-lg text-xs hover:bg-accent cursor-pointer flex justify-between"
                >
                  <span className="font-medium">{r.area_label}</span>
                  <span className="text-muted-foreground text-[10px]">
                    {r.coarse_lat}, {r.coarse_lng}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                Search Radius
              </Label>
              <Select
                value={radiusKm.toString()}
                onValueChange={(val) => setRadiusKm(parseInt(val))}
              >
                <SelectTrigger className="h-9 text-xs mt-1">
                  <SelectValue placeholder="Radius" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 km</SelectItem>
                  <SelectItem value="3">3 km</SelectItem>
                  <SelectItem value="5">5 km</SelectItem>
                  <SelectItem value="10">10 km (Standard)</SelectItem>
                  <SelectItem value="25">25 km</SelectItem>
                  <SelectItem value="0">Remote Only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                Invisible Mode
              </Label>
              <div className="flex items-center justify-between p-2 rounded-xl border mt-1">
                <span className="text-xs font-semibold">Hide from discovery</span>
                <Switch checked={isInvisible} onCheckedChange={setIsInvisible} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
