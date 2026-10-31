"use client";

import * as React from "react";
import { Plus, Trash2, Clock, Calendar as CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProposedSlot } from "@/types/swap";

interface SlotPickerProps {
  slots: ProposedSlot[];
  onChange: (slots: ProposedSlot[]) => void;
  maxSlots?: number;
}

interface LocalSlot {
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
}

export function SlotPicker({ slots, onChange, maxSlots = 3 }: SlotPickerProps) {
  // Convert incoming ISO UTC slots to local date & time strings
  const [localSlots, setLocalSlots] = React.useState<LocalSlot[]>(() => {
    if (slots.length > 0) {
      return slots.map((s) => {
        const d = new Date(s.start_time_utc);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, "0");
        const dd = String(d.getDate()).padStart(2, "0");
        const hh = String(d.getHours()).padStart(2, "0");
        const min = String(d.getMinutes()).padStart(2, "0");
        return {
          date: `${yyyy}-${mm}-${dd}`,
          time: `${hh}:${min}`,
        };
      });
    }

    // Default: tomorrow at 10:00 AM
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const yyyy = tomorrow.getFullYear();
    const mm = String(tomorrow.getMonth() + 1).padStart(2, "0");
    const dd = String(tomorrow.getDate()).padStart(2, "0");
    return [{ date: `${yyyy}-${mm}-${dd}`, time: "10:00" }];
  });

  // Today's date string for input min attribute
  const todayStr = React.useMemo(() => {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }, []);

  const syncToParent = React.useCallback(
    (newLocal: LocalSlot[]) => {
      const converted: ProposedSlot[] = [];
      for (const item of newLocal) {
        if (!item.date || !item.time) continue;
        const [year, month, day] = item.date.split("-").map(Number);
        const [hour, min] = item.time.split(":").map(Number);
        const start = new Date(year, month - 1, day, hour, min, 0);
        const end = new Date(start.getTime() + 30 * 60 * 1000); // exactly 30 minutes

        converted.push({
          start_time_utc: start.toISOString(),
          end_time_utc: end.toISOString(),
        });
      }
      onChange(converted);
    },
    [onChange]
  );

  // Sync initial state once on mount if parent is empty
  React.useEffect(() => {
    if (slots.length === 0 && localSlots.length > 0) {
      syncToParent(localSlots);
    }
  }, [localSlots, slots.length, syncToParent]);

  const handleUpdate = (idx: number, field: "date" | "time", value: string) => {
    const updated = localSlots.map((s, i) => (i === idx ? { ...s, [field]: value } : s));
    setLocalSlots(updated);
    syncToParent(updated);
  };

  const handleAdd = () => {
    if (localSlots.length >= maxSlots) return;
    const last = localSlots[localSlots.length - 1];
    // Default next slot 1 hour after or next day
    const updated = [...localSlots, { date: last.date, time: "14:00" }];
    setLocalSlots(updated);
    syncToParent(updated);
  };

  const handleRemove = (idx: number) => {
    if (localSlots.length <= 1) return;
    const updated = localSlots.filter((_, i) => i !== idx);
    setLocalSlots(updated);
    syncToParent(updated);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-semibold flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-primary" />
          Proposed 30-Minute Time Slots ({localSlots.length}/{maxSlots})
        </Label>
        {localSlots.length < maxSlots && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAdd}
            className="h-8 text-xs gap-1"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Alternative Slot
          </Button>
        )}
      </div>

      <div className="space-y-3">
        {localSlots.map((slot, idx) => (
          <div
            key={idx}
            className="p-3 bg-muted/40 border rounded-lg space-y-2 relative group hover:border-primary/50 transition-colors"
          >
            <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
              <span>Slot {idx + 1} &bull; 30-minute block</span>
              {localSlots.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:text-destructive"
                  onClick={() => handleRemove(idx)}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">Date</Label>
                <div className="relative">
                  <Input
                    type="date"
                    min={todayStr}
                    value={slot.date}
                    onChange={(e) => handleUpdate(idx, "date", e.target.value)}
                    className="h-9 text-xs"
                    required
                  />
                </div>
              </div>

              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">Start Time (Your Timezone)</Label>
                <Input
                  type="time"
                  value={slot.time}
                  onChange={(e) => handleUpdate(idx, "time", e.target.value)}
                  className="h-9 text-xs"
                  required
                />
              </div>
            </div>

            {slot.date && slot.time && (
              <div className="text-[11px] text-muted-foreground flex items-center gap-1 pt-1">
                <CalendarIcon className="w-3 h-3 text-primary" />
                <span>
                  Half 1: {slot.time} &rarr;{" "}
                  {(() => {
                    const [h, m] = slot.time.split(":").map(Number);
                    const endMin = (m + 30) % 60;
                    const endHr = h + Math.floor((m + 30) / 60);
                    return `${String(endHr).padStart(2, "0")}:${String(endMin).padStart(2, "0")}`;
                  })()}{" "}
                  (30m) &bull; Followed immediately by Half 2 (30m)
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
