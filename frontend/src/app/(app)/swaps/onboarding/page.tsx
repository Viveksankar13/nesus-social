"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  Compass,
  GraduationCap,
  MapPin,
  Plus,
  Search,
  Shield,
  Sparkles,
  Trash2,
  Video,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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

export default function SwapOnboardingPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = React.useState<number>(1);

  // Form State
  const [bio, setBio] = React.useState("");
  const [teachSkills, setTeachSkills] = React.useState<UserSkill[]>([]);
  const [learnSkills, setLearnSkills] = React.useState<UserSkill[]>([]);
  const [availabilityWindows, setAvailabilityWindows] = React.useState<
    AvailabilityWindow[]
  >([
    { day_of_week: 0, start_time_utc: "09:00", end_time_utc: "17:00" },
    { day_of_week: 2, start_time_utc: "09:00", end_time_utc: "17:00" },
    { day_of_week: 5, start_time_utc: "10:00", end_time_utc: "16:00" },
  ]);
  const [areaLabel, setAreaLabel] = React.useState("");
  const [coarseLat, setCoarseLat] = React.useState<number | null>(null);
  const [coarseLng, setCoarseLng] = React.useState<number | null>(null);
  const [radiusKm, setRadiusKm] = React.useState<number>(10);
  const [modes, setModes] = React.useState<string[]>(["video", "in_person"]);
  const [is18Confirmed, setIs18Confirmed] = React.useState<boolean>(false);
  const [acceptsNewcomers, setAcceptsNewcomers] = React.useState<boolean>(true);

  // Skill Search State
  const [skillSearch, setSkillSearch] = React.useState("");
  const [selectedCategory, setSelectedCategory] = React.useState<string>("All");
  const [customSkillName, setCustomSkillName] = React.useState("");

  // Geocode Search State
  const [geoQuery, setGeoQuery] = React.useState("");
  const [geoResults, setGeoResults] = React.useState<GeocodeSearchResult[]>([]);
  const [isSearchingGeo, setIsSearchingGeo] = React.useState(false);

  // Fetch Existing Profile
  const { data: myProfile, isLoading: isProfileLoading } = useQuery({
    queryKey: ["swap-profile", "me"],
    queryFn: swapApi.getMyProfile,
  });

  // Fetch Canonical Taxonomy
  const { data: taxonomy = [] } = useQuery({
    queryKey: ["swap-taxonomy"],
    queryFn: swapApi.getTaxonomy,
  });

  // Populate existing data when loaded
  React.useEffect(() => {
    if (myProfile) {
      if (myProfile.bio) setBio(myProfile.bio);
      if (myProfile.teach_skills.length > 0) setTeachSkills(myProfile.teach_skills);
      if (myProfile.learn_skills.length > 0) setLearnSkills(myProfile.learn_skills);
      if (myProfile.availability_windows.length > 0)
        setAvailabilityWindows(myProfile.availability_windows);
      if (myProfile.area_label) setAreaLabel(myProfile.area_label);
      if (myProfile.coarse_lat !== null) setCoarseLat(myProfile.coarse_lat);
      if (myProfile.coarse_lng !== null) setCoarseLng(myProfile.coarse_lng);
      if (myProfile.radius_km !== undefined) setRadiusKm(myProfile.radius_km);
      if (myProfile.modes.length > 0) setModes(myProfile.modes);
      setIs18Confirmed(myProfile.is_18_confirmed);
      setAcceptsNewcomers(myProfile.accepts_newcomers);
    }
  }, [myProfile]);

  // Flattened and filtered skills
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

  // Geocode Search Debounced
  React.useEffect(() => {
    if (geoQuery.trim().length < 2) {
      setGeoResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearchingGeo(true);
      try {
        const results = await swapApi.geocodeLocation(geoQuery);
        setGeoResults(results);
      } catch {
        setGeoResults([]);
      } finally {
        setIsSearchingGeo(false);
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
        is_18_confirmed: is18Confirmed,
        accepts_newcomers: acceptsNewcomers,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["swap-profile"] });
      router.push("/swaps");
    },
  });

  // Suggest Skill Mutation
  const suggestMutation = useMutation({
    mutationFn: () => swapApi.suggestSkill(customSkillName, "General"),
    onSuccess: (newSkill) => {
      queryClient.invalidateQueries({ queryKey: ["swap-taxonomy"] });
      if (step === 1) {
        handleAddTeachSkill(newSkill.slug, newSkill.display_name);
      } else if (step === 2) {
        handleAddLearnSkill(newSkill.slug, newSkill.display_name);
      }
      setCustomSkillName("");
    },
  });

  // Handlers for Teaching Skills
  const handleAddTeachSkill = (slug: string, displayName?: string) => {
    if (teachSkills.some((s) => s.skill_slug === slug)) return;
    setTeachSkills([
      ...teachSkills,
      {
        skill_slug: slug,
        skill_type: "teach",
        level: "intermediate",
        years_experience: 1,
        notes: `Happy to mentor in ${displayName || slug}.`,
      },
    ]);
  };

  const handleRemoveTeachSkill = (slug: string) => {
    setTeachSkills(teachSkills.filter((s) => s.skill_slug !== slug));
  };

  // Handlers for Learning Skills
  const handleAddLearnSkill = (slug: string, displayName?: string) => {
    if (learnSkills.some((s) => s.skill_slug === slug)) return;
    setLearnSkills([
      ...learnSkills,
      {
        skill_slug: slug,
        skill_type: "learn",
        level: "beginner",
        years_experience: 0,
        notes: `Eager to learn fundamentals of ${displayName || slug}.`,
      },
    ]);
  };

  const handleRemoveLearnSkill = (slug: string) => {
    setLearnSkills(learnSkills.filter((s) => s.skill_slug !== slug));
  };

  // Availability Window Handlers
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

  // Mode Toggle
  const handleToggleMode = (mode: string) => {
    if (modes.includes(mode)) {
      if (modes.length > 1) {
        setModes(modes.filter((m) => m !== mode));
      }
    } else {
      setModes([...modes, mode]);
    }
  };

  if (isProfileLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Skill Swap Onboarding</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight">
          Welcome to the Skill Swap Economy
        </h1>
        <p className="text-muted-foreground mt-2 max-w-lg mx-auto text-sm">
          Exchange 30 minutes of peer tutoring for 30 minutes of learning. No money,
          zero friction, pure peer-to-peer reciprocity.
        </p>
      </div>

      {/* Progress Steps */}
      <div className="grid grid-cols-4 gap-2 mb-8">
        {[
          { num: 1, title: "I Can Teach", icon: GraduationCap },
          { num: 2, title: "I Want to Learn", icon: BookOpen },
          { num: 3, title: "Availability", icon: Calendar },
          { num: 4, title: "Preferences", icon: Compass },
        ].map((s) => {
          const Icon = s.icon;
          const isActive = step === s.num;
          const isDone = step > s.num;
          return (
            <div
              key={s.num}
              onClick={() => isDone && setStep(s.num)}
              className={`flex flex-col items-center p-3 rounded-xl border text-center transition-all ${
                isActive
                  ? "border-primary bg-primary/5 text-primary shadow-sm"
                  : isDone
                  ? "border-muted bg-muted/30 text-foreground cursor-pointer hover:bg-muted/50"
                  : "border-border/40 opacity-60 text-muted-foreground"
              }`}
            >
              <div
                className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold mb-1 ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : isDone
                    ? "bg-green-500 text-white"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {isDone ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
              </div>
              <span className="text-xs font-medium hidden sm:inline">{s.title}</span>
            </div>
          );
        })}
      </div>

      {/* Step Content Container */}
      <div className="bg-card rounded-2xl border p-6 sm:p-8 shadow-sm">
        {/* ── STEP 1: SKILLS I CAN TEACH ───────────────────────────────── */}
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <GraduationCap className="h-5 w-5 text-primary" />
                <span>What skills can you teach or share?</span>
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                Select 1 or more skills where you can offer 30 minutes of friendly guidance.
              </p>
            </div>

            {/* Selected Skills List */}
            {teachSkills.length > 0 && (
              <div className="space-y-3">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Your Selected Teaching Skills ({teachSkills.length})
                </Label>
                <div className="grid gap-3">
                  {teachSkills.map((ts) => (
                    <div
                      key={ts.skill_slug}
                      className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3.5 rounded-xl border bg-accent/30 gap-3"
                    >
                      <div className="flex-1">
                        <span className="font-semibold text-sm capitalize">
                          {ts.skill_slug.replace(/-/g, " ")}
                        </span>
                        <div className="flex flex-wrap gap-2 mt-1.5">
                          <Select
                            value={ts.level}
                            onValueChange={(
                              val: "beginner" | "intermediate" | "advanced" | "expert"
                            ) =>
                              setTeachSkills(
                                teachSkills.map((item) =>
                                  item.skill_slug === ts.skill_slug
                                    ? { ...item, level: val }
                                    : item
                                )
                              )
                            }
                          >
                            <SelectTrigger className="h-7 text-xs w-32">
                              <SelectValue placeholder="Level" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="beginner">Beginner</SelectItem>
                              <SelectItem value="intermediate">Intermediate</SelectItem>
                              <SelectItem value="advanced">Advanced</SelectItem>
                              <SelectItem value="expert">Expert</SelectItem>
                            </SelectContent>
                          </Select>

                          <Input
                            type="number"
                            min="0"
                            max="50"
                            placeholder="Yrs exp"
                            value={ts.years_experience ?? ""}
                            onChange={(e) =>
                              setTeachSkills(
                                teachSkills.map((item) =>
                                  item.skill_slug === ts.skill_slug
                                    ? {
                                        ...item,
                                        years_experience: parseInt(e.target.value) || 0,
                                      }
                                    : item
                                )
                              )
                            }
                            className="h-7 text-xs w-20"
                          />
                        </div>
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveTeachSkill(ts.skill_slug)}
                        className="text-destructive hover:bg-destructive/10 h-8 px-2"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Skill Selector Filter & Search */}
            <div className="space-y-3 pt-2">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                Browse or Search Taxonomy
              </Label>
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search skills (e.g. Python, Spanish, Guitar)..."
                    value={skillSearch}
                    onChange={(e) => setSkillSearch(e.target.value)}
                    className="pl-9 h-10"
                  />
                </div>
                <Select
                  value={selectedCategory}
                  onValueChange={(v) => setSelectedCategory(v)}
                >
                  <SelectTrigger className="w-full sm:w-48 h-10">
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Categories</SelectItem>
                    {taxonomy.map((c) => (
                      <SelectItem key={c.category} value={c.category}>
                        {c.category}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Skills Pill Cloud */}
              <div className="flex flex-wrap gap-2 max-h-56 overflow-y-auto p-2 rounded-xl border bg-muted/20">
                {allSkills.map((s) => {
                  const isSelected = teachSkills.some((ts) => ts.skill_slug === s.slug);
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() =>
                        isSelected
                          ? handleRemoveTeachSkill(s.slug)
                          : handleAddTeachSkill(s.slug, s.display_name)
                      }
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        isSelected
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "bg-card hover:bg-accent border text-foreground"
                      }`}
                    >
                      <span>{s.display_name}</span>
                      {isSelected ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : (
                        <Plus className="h-3.5 w-3.5 opacity-60" />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Suggest Skill If Missing */}
              <div className="flex items-center gap-2 pt-2 text-xs">
                <span className="text-muted-foreground">Don&apos;t see your skill?</span>
                <Input
                  placeholder="New skill name..."
                  value={customSkillName}
                  onChange={(e) => setCustomSkillName(e.target.value)}
                  className="h-8 max-w-xs text-xs"
                />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!customSkillName.trim() || suggestMutation.isPending}
                  onClick={() => suggestMutation.mutate()}
                  className="h-8 text-xs"
                >
                  {suggestMutation.isPending ? "Adding..." : "Add Custom"}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 2: SKILLS I WANT TO LEARN ───────────────────────────── */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                <span>What skills do you want to learn?</span>
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                Tell us what you are curious about or need peer help with.
              </p>
            </div>

            {/* Selected Learning Skills */}
            {learnSkills.length > 0 && (
              <div className="space-y-3">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Your Wanted Skills ({learnSkills.length})
                </Label>
                <div className="grid gap-3">
                  {learnSkills.map((ls) => (
                    <div
                      key={ls.skill_slug}
                      className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3.5 rounded-xl border bg-accent/30 gap-3"
                    >
                      <div className="flex-1">
                        <span className="font-semibold text-sm capitalize">
                          {ls.skill_slug.replace(/-/g, " ")}
                        </span>
                        <div className="flex flex-wrap gap-2 mt-1.5">
                          <Select
                            value={ls.level}
                            onValueChange={(
                              val: "beginner" | "intermediate" | "advanced" | "expert"
                            ) =>
                              setLearnSkills(
                                learnSkills.map((item) =>
                                  item.skill_slug === ls.skill_slug
                                    ? { ...item, level: val }
                                    : item
                                )
                              )
                            }
                          >
                            <SelectTrigger className="h-7 text-xs w-36">
                              <SelectValue placeholder="Current Level" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="beginner">Absolute Beginner</SelectItem>
                              <SelectItem value="intermediate">Some Basics</SelectItem>
                              <SelectItem value="advanced">Intermediate</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveLearnSkill(ls.skill_slug)}
                        className="text-destructive hover:bg-destructive/10 h-8 px-2"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Browse & Search */}
            <div className="space-y-3 pt-2">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                Browse Skills to Learn
              </Label>
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search topics (e.g. Algorithms, Conversational French, Figma)..."
                    value={skillSearch}
                    onChange={(e) => setSkillSearch(e.target.value)}
                    className="pl-9 h-10"
                  />
                </div>
                <Select
                  value={selectedCategory}
                  onValueChange={(v) => setSelectedCategory(v)}
                >
                  <SelectTrigger className="w-full sm:w-48 h-10">
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Categories</SelectItem>
                    {taxonomy.map((c) => (
                      <SelectItem key={c.category} value={c.category}>
                        {c.category}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Skills Pill Cloud */}
              <div className="flex flex-wrap gap-2 max-h-56 overflow-y-auto p-2 rounded-xl border bg-muted/20">
                {allSkills.map((s) => {
                  const isSelected = learnSkills.some((ls) => ls.skill_slug === s.slug);
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() =>
                        isSelected
                          ? handleRemoveLearnSkill(s.slug)
                          : handleAddLearnSkill(s.slug, s.display_name)
                      }
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        isSelected
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "bg-card hover:bg-accent border text-foreground"
                      }`}
                    >
                      <span>{s.display_name}</span>
                      {isSelected ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : (
                        <Plus className="h-3.5 w-3.5 opacity-60" />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Suggest Custom */}
              <div className="flex items-center gap-2 pt-2 text-xs">
                <span className="text-muted-foreground">Want to learn something else?</span>
                <Input
                  placeholder="Topic name..."
                  value={customSkillName}
                  onChange={(e) => setCustomSkillName(e.target.value)}
                  className="h-8 max-w-xs text-xs"
                />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!customSkillName.trim() || suggestMutation.isPending}
                  onClick={() => suggestMutation.mutate()}
                  className="h-8 text-xs"
                >
                  {suggestMutation.isPending ? "Adding..." : "Add Topic"}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 3: WEEKLY AVAILABILITY ──────────────────────────────── */}
        {step === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Calendar className="h-5 w-5 text-primary" />
                <span>When are you typically available?</span>
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                Configure your recurring weekly 30-minute peer swap windows. Stored in
                UTC and automatically converted to each viewer&apos;s local timezone.
              </p>
            </div>

            <div className="grid gap-3">
              {DAYS_OF_WEEK.map((dayName, dayIndex) => {
                const window = availabilityWindows.find(
                  (w) => w.day_of_week === dayIndex
                );
                const isEnabled = !!window;

                return (
                  <div
                    key={dayName}
                    className={`flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border transition-all ${
                      isEnabled ? "bg-accent/40 border-primary/40" : "bg-card border-border/50 opacity-70"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Switch
                        checked={isEnabled}
                        onCheckedChange={() => handleToggleDay(dayIndex)}
                      />
                      <span className="font-semibold text-sm w-28">{dayName}</span>
                    </div>

                    {isEnabled && (
                      <div className="flex items-center gap-2 mt-2 sm:mt-0 text-xs">
                        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                        <Input
                          type="time"
                          value={window?.start_time_utc || "09:00"}
                          onChange={(e) =>
                            handleUpdateTime(dayIndex, "start_time_utc", e.target.value)
                          }
                          className="h-8 w-28 text-xs"
                        />
                        <span className="text-muted-foreground">to</span>
                        <Input
                          type="time"
                          value={window?.end_time_utc || "17:00"}
                          onChange={(e) =>
                            handleUpdateTime(dayIndex, "end_time_utc", e.target.value)
                          }
                          className="h-8 w-28 text-xs"
                        />
                        <span className="text-xs text-muted-foreground ml-1">UTC</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── STEP 4: PREFERENCES & LOCATION PRIVACY ───────────────────── */}
        {step === 4 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Compass className="h-5 w-5 text-primary" />
                <span>Location & Privacy Preferences</span>
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                We protect your safety. Your exact address and coordinates are{" "}
                <strong>never stored or shared</strong>. Peers only see your generalized
                neighborhood label and a distance bucket.
              </p>
            </div>

            {/* Neighborhood / Area Search */}
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                Your General Area / Neighborhood
              </Label>
              <div className="relative">
                <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search city, district, or neighborhood (e.g. Mission District, San Francisco)..."
                  value={geoQuery || areaLabel}
                  onChange={(e) => {
                    setGeoQuery(e.target.value);
                    setAreaLabel(e.target.value);
                  }}
                  className="pl-9 pr-9 h-10"
                />
                {isSearchingGeo && (
                  <div className="absolute right-3 top-3 h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                )}
              </div>

              {/* Geocode Search Results Dropdown */}
              {geoResults.length > 0 && (
                <div className="rounded-xl border bg-card p-2 shadow-md space-y-1 mt-1">
                  {geoResults.map((res, i) => (
                    <div
                      key={i}
                      onClick={() => {
                        setAreaLabel(res.area_label);
                        setCoarseLat(res.coarse_lat);
                        setCoarseLng(res.coarse_lng);
                        setGeoQuery(res.area_label);
                        setGeoResults([]);
                      }}
                      className="px-3 py-2 rounded-lg text-xs hover:bg-accent cursor-pointer flex items-center justify-between"
                    >
                      <span className="font-medium">{res.area_label}</span>
                      <span className="text-muted-foreground text-[10px]">
                        Coarse: {res.coarse_lat}, {res.coarse_lng}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {areaLabel && (
                <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400 mt-1">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Selected Area: {areaLabel}</span>
                </div>
              )}
            </div>

            {/* Radius & Modes */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  In-Person Match Radius
                </Label>
                <Select
                  value={radiusKm.toString()}
                  onValueChange={(val) => setRadiusKm(parseInt(val))}
                >
                  <SelectTrigger className="h-10">
                    <SelectValue placeholder="Radius" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Within 1 km (Walking distance)</SelectItem>
                    <SelectItem value="3">Within 3 km</SelectItem>
                    <SelectItem value="5">Within 5 km</SelectItem>
                    <SelectItem value="10">Within 10 km (Standard)</SelectItem>
                    <SelectItem value="25">Within 25 km</SelectItem>
                    <SelectItem value="0">Remote Only (No in-person)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Exchange Modes
                </Label>
                <div className="flex gap-2">
                  {[
                    { id: "video", label: "Video Call", icon: Video },
                    { id: "in_person", label: "Public In-Person", icon: MapPin },
                  ].map((m) => {
                    const isSelected = modes.includes(m.id);
                    const Icon = m.icon;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => handleToggleMode(m.id)}
                        className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-lg border text-xs font-medium transition-all ${
                          isSelected
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border text-muted-foreground hover:bg-accent"
                        }`}
                      >
                        <Icon className="h-3.5 w-3.5" />
                        <span>{m.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Bio */}
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                Short Swap Bio
              </Label>
              <Textarea
                placeholder="Share a sentence about your background, interests, or what makes you excited to swap skills..."
                value={bio}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setBio(e.target.value)
                }
                maxLength={500}
                className="h-20 text-xs"
              />
            </div>

            {/* Newcomers & 18+ Confirmation */}
            <div className="space-y-3 pt-2 border-t">
              <div className="flex items-center justify-between p-3 rounded-xl border bg-muted/20">
                <div className="pr-4">
                  <p className="text-xs font-semibold text-foreground">
                    Accept swap requests from newcomers
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    Allow members with 0 completed swaps to propose exchanges with you.
                  </p>
                </div>
                <Switch
                  checked={acceptsNewcomers}
                  onCheckedChange={setAcceptsNewcomers}
                />
              </div>

              <div className="flex items-start gap-3 p-3.5 rounded-xl border border-amber-500/30 bg-amber-50/50 dark:bg-amber-950/20">
                <Shield className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="age18"
                      checked={is18Confirmed}
                      onChange={(e) => setIs18Confirmed(e.target.checked)}
                      className="rounded border-gray-300 text-primary focus:ring-primary h-4 w-4"
                    />
                    <label
                      htmlFor="age18"
                      className="text-xs font-semibold text-foreground cursor-pointer"
                    >
                      I confirm I am 18 years of age or older.
                    </label>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Nexus Skill Swap enforces a strict 18+ safety policy. In-person swaps
                    must occur in public venues (libraries, cafes, campus lounges).
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Navigation Footer ────────────────────────────────────────── */}
        <div className="flex items-center justify-between pt-6 mt-6 border-t">
          {step > 1 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setStep(step - 1)}
              className="gap-1.5"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Back</span>
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push("/swaps")}
              className="text-muted-foreground"
            >
              Skip for now
            </Button>
          )}

          {step < 4 ? (
            <Button
              size="sm"
              onClick={() => setStep(step + 1)}
              className="gap-1.5 shadow-sm"
            >
              <span>Continue</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="sm"
              disabled={!is18Confirmed || saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
              className="gap-1.5 bg-primary shadow-sm"
            >
              {saveMutation.isPending ? (
                "Saving Profile..."
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Complete Onboarding</span>
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
