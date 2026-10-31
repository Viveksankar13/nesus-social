"use client";

import React, { useMemo } from "react";
import { MapContainer, TileLayer, Circle, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { SwapListing } from "@/types/swap";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { MapPin, ArrowRight, ShieldCheck } from "lucide-react";

interface SwapMapProps {
  listings: SwapListing[];
  center?: [number, number];
  zoom?: number;
}

// Known approximate coarse cluster centers for demo areas (privacy-safe, ~1km grid)
const AREA_CENTROIDS: Record<string, [number, number]> = {
  "downtown tech hub": [12.9716, 77.5946],
  "university campus": [12.9784, 77.5698],
  "indiranagar": [12.9784, 77.6408],
  "koramangala": [12.9352, 77.6245],
  "mg road": [12.9756, 77.6066],
  "whitefield": [12.9698, 77.7499],
  "hsr layout": [12.9121, 77.6446],
  "default": [12.9716, 77.5946],
};

export default function SwapMap({
  listings,
  center = [12.9716, 77.5946],
  zoom = 12,
}: SwapMapProps) {
  // Group listings by area label (privacy: circular bubbles, never pins)
  const clusters = useMemo(() => {
    const map = new Map<string, { label: string; coords: [number, number]; items: SwapListing[] }>();

    listings.forEach((listing, index) => {
      const rawLabel = (listing.area_label || "Downtown Tech Hub").toLowerCase().trim();
      const coords = AREA_CENTROIDS[rawLabel] || [
        center[0] + ((index % 5) - 2) * 0.018,
        center[1] + ((Math.floor(index / 5) % 5) - 2) * 0.018,
      ];

      const key = rawLabel;
      if (!map.has(key)) {
        map.set(key, {
          label: listing.area_label || "Downtown Tech Hub",
          coords,
          items: [],
        });
      }
      map.get(key)!.items.push(listing);
    });

    return Array.from(map.values());
  }, [listings, center]);

  return (
    <div className="relative w-full h-[540px] rounded-2xl overflow-hidden border border-border shadow-sm">
      <div className="absolute top-3 left-3 z-[1000] bg-background/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-border text-xs flex items-center gap-1.5 shadow-md">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
        <span className="font-medium text-foreground">Coarse area view</span>
        <span className="text-muted-foreground">• exact pins hidden for privacy</span>
      </div>

      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={false}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {clusters.map((cluster) => {
          const count = cluster.items.length;
          const radiusMeters = Math.min(1400, 700 + count * 150);

          return (
            <Circle
              key={cluster.label}
              center={cluster.coords}
              radius={radiusMeters}
              pathOptions={{
                color: "#6366f1",
                fillColor: "#818cf8",
                fillOpacity: 0.25,
                weight: 2,
              }}
            >
              <Popup className="swap-popup">
                <div className="p-2 min-w-[220px] max-w-[280px]">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <MapPin className="w-4 h-4 text-indigo-500" />
                    <span className="font-semibold text-sm text-foreground">
                      {cluster.label}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">
                    {count} active skill swap {count === 1 ? "offer" : "offers"} in this area
                  </p>

                  <div className="space-y-1.5 max-h-[160px] overflow-y-auto">
                    {cluster.items.map((item) => (
                      <div
                        key={item.id}
                        className="p-1.5 rounded-md bg-muted/50 border border-border/50 text-xs"
                      >
                        <p className="font-medium truncate text-foreground">{item.title}</p>
                        <div className="flex items-center justify-between mt-1">
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                            {item.skill_offered.display_name}
                          </Badge>
                          <Link href={`/swaps/${item.id}`}>
                            <span className="text-primary hover:underline text-[11px] font-medium flex items-center gap-0.5">
                              View <ArrowRight className="w-2.5 h-2.5" />
                            </span>
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Popup>
            </Circle>
          );
        })}
      </MapContainer>
    </div>
  );
}
