"""
Skill Swap Geocoding & Privacy Distance Calculation
===================================================
Provides coarse geocoding via Open-Meteo and privacy-preserving distance bucketing.
Zero API keys required.
Coordinates are strictly coarsened (~1 km grid, round to 2 decimal places).
Precise coordinates are NEVER passed to clients.
"""

import math
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.swap import GeocodeSearchResult

logger = get_logger(__name__)

OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


def coarsen_coord(val: float | None) -> float | None:
    """Coarsen coordinate to ~1.1 km grid (2 decimal places)."""
    return round(val, 2) if val is not None else None


def calculate_haversine_km(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """
    Calculate great-circle distance between two points in kilometers.
    """
    r = 6371.0  # Earth's mean radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def get_distance_bucket(
    viewer_lat: float | None,
    viewer_lng: float | None,
    target_lat: float | None,
    target_lng: float | None,
) -> str:
    """
    Categorize distance into safe, coarse human-readable buckets.
    Returns 'remote' if either location is missing or distance exceeds 25 km.
    """
    if (
        viewer_lat is None
        or viewer_lng is None
        or target_lat is None
        or target_lng is None
    ):
        return "remote"

    dist = calculate_haversine_km(viewer_lat, viewer_lng, target_lat, target_lng)

    if dist < 1.0:
        return "under 1 km"
    if dist < 3.0:
        return "1–3 km"
    if dist < 5.0:
        return "3–5 km"
    if dist < 10.0:
        return "5–10 km"
    if dist <= 25.0:
        return "10–25 km"
    return "remote"


async def search_coarse_locations(query: str, count: int = 5) -> list[GeocodeSearchResult]:
    """
    Query Open-Meteo Geocoding API and return results with coarse coordinates.
    """
    clean_query = query.strip()
    if len(clean_query) < 2:
        return []

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                OPEN_METEO_GEOCODE_URL,
                params={
                    "name": clean_query,
                    "count": count,
                    "language": "en",
                    "format": "json",
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    f"Open-Meteo geocoding request returned {resp.status_code}: {resp.text}"
                )
                return []

            data = resp.json()
            results_raw: list[dict[str, Any]] = data.get("results") or []
            out: list[GeocodeSearchResult] = []

            for r in results_raw:
                name = r.get("name", "")
                admin1 = r.get("admin1")
                country = r.get("country")
                parts = [p for p in [name, admin1, country] if p]
                area_label = ", ".join(parts)

                lat = float(r["latitude"])
                lng = float(r["longitude"])

                out.append(
                    GeocodeSearchResult(
                        name=name,
                        area_label=area_label,
                        coarse_lat=coarsen_coord(lat) or 0.0,
                        coarse_lng=coarsen_coord(lng) or 0.0,
                        country=country,
                        admin1=admin1,
                    )
                )
            return out
    except Exception as e:
        logger.warning(f"Error calling Open-Meteo geocoding: {e}")
        return []
