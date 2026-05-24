import requests

_HEADERS = {"User-Agent": "AIMedicalAssistant/1.0"}


def _get_location():
    try:
        r = requests.get("http://ip-api.com/json/", timeout=6, headers=_HEADERS)
        d = r.json()
        if d.get("status") == "success":
            return d.get("lat"), d.get("lon"), d.get("city", "your area")
    except Exception:
        pass
    return None, None, None


def _search_nominatim(lat, lon, radius_km):
    """Search hospitals via Nominatim OSM — reliable, no rate-limit issues."""
    delta = radius_km * 0.009
    params = {
        "amenity": "hospital",
        "format": "json",
        "limit": 8,
        "bounded": 1,
        "viewbox": f"{lon-delta},{lat+delta},{lon+delta},{lat-delta}",
        "addressdetails": 0,
    }
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=_HEADERS,
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def _search_overpass(lat, lon, radius_km):
    """Fallback: Overpass API for richer tag data (phone numbers etc.)."""
    delta = radius_km * 0.009
    q = (
        f"[out:json][timeout:20];"
        f"(node[\"amenity\"=\"hospital\"]({lat-delta},{lon-delta},{lat+delta},{lon+delta});"
        f"way[\"amenity\"=\"hospital\"]({lat-delta},{lon-delta},{lat+delta},{lon+delta}););"
        f"out center 6;"
    )
    for url in [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]:
        try:
            r = requests.get(url, params={"data": q}, timeout=20, headers=_HEADERS)
            if r.status_code == 200 and r.text.strip():
                return r.json().get("elements", [])
        except Exception:
            continue
    return []


def _format_nominatim(results, city, radius_km):
    lines = [f"🏥 **Hospitals near {city}** (within {radius_km} km)\n"]
    for h in results[:6]:
        name = h.get("name") or h.get("display_name", "Hospital").split(",")[0]
        h_lat = h.get("lat")
        h_lon = h.get("lon")
        entry = [f"**{name}**"]
        if h_lat and h_lon:
            entry.append(f"[📍 Open in Maps](https://maps.google.com/?q={h_lat},{h_lon})")
        lines.append("\n".join(entry))
    return "\n\n---\n\n".join(lines)


def _format_overpass(elements, city, radius_km):
    lines = [f"🏥 **Hospitals near {city}** (within {radius_km} km)\n"]
    for el in elements[:6]:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en") or "Hospital"
        if el.get("type") == "node":
            h_lat, h_lon = el.get("lat"), el.get("lon")
        else:
            c = el.get("center", {})
            h_lat, h_lon = c.get("lat"), c.get("lon")

        phone = tags.get("phone") or tags.get("contact:phone") or ""
        entry = [f"**{name}**"]
        if phone:
            entry.append(f"📞 {phone}")
        if h_lat and h_lon:
            entry.append(f"[📍 Open in Maps](https://maps.google.com/?q={h_lat},{h_lon})")
        lines.append("\n".join(entry))
    return "\n\n---\n\n".join(lines)


def find_nearby_hospitals():
    lat, lon, city = _get_location()

    if not lat or not lon:
        return (
            "⚠️ Could not detect your location.\n\n"
            "**Emergency:** 📞 **112** (India) · **911** (US)"
        )

    # Try progressively larger search areas
    for radius in [15, 30, 50]:
        # Primary: Nominatim
        results = _search_nominatim(lat, lon, radius)
        if results:
            return _format_nominatim(results, city, radius)

        # Fallback: Overpass
        elements = _search_overpass(lat, lon, radius)
        if elements:
            return _format_overpass(elements, city, radius)

    return (
        f"No hospitals found near **{city}** in OpenStreetMap data.\n\n"
        "**Emergency:** 📞 **112** (India) · **911** (US)\n\n"
        f"Try searching: [Hospitals near {city}](https://www.google.com/maps/search/hospital+near+{city.replace(' ', '+')})"
    )
