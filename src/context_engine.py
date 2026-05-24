import time
import requests
from datetime import datetime

_cache = {"value": None, "ts": 0}
_CACHE_TTL = 600  # 10 minutes


def get_user_location():
    try:
        r = requests.get("http://ip-api.com/json/", timeout=5)
        data = r.json()
        if data.get("status") == "success":
            return {
                "city": data.get("city", "Unknown"),
                "region": data.get("regionName", ""),
                "country": data.get("country", "Unknown"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
            }
    except Exception:
        pass
    return None


def get_weather(lat, lon):
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,weathercode,windspeed_10m"
            "&timezone=auto"
        )
        r = requests.get(url, timeout=5)
        data = r.json()
        current = data.get("current", {})
        return {
            "temp_c": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "windspeed": current.get("windspeed_10m"),
            "code": current.get("weathercode"),
            "condition": _weather_code_label(current.get("weathercode")),
        }
    except Exception:
        return None


def _weather_code_label(code):
    if code is None:
        return "Unknown"
    if code == 0:
        return "Clear sky"
    if code in [1, 2, 3]:
        return "Partly cloudy"
    if code in [45, 48]:
        return "Foggy"
    if code in [51, 53, 55, 56, 57]:
        return "Drizzle"
    if code in [61, 63, 65, 66, 67]:
        return "Rainy"
    if code in [71, 73, 75, 77]:
        return "Snowy"
    if code in [80, 81, 82]:
        return "Rain showers"
    if code in [85, 86]:
        return "Snow showers"
    if code in [95, 96, 99]:
        return "Thunderstorm"
    return "Cloudy"


def get_season(lat, lon):
    month = datetime.now().month
    # India-specific seasons
    if lat is not None and 8 <= lat <= 37 and lon is not None and 68 <= lon <= 97:
        if month in [3, 4, 5]:
            return "Summer"
        if month in [6, 7, 8, 9]:
            return "Monsoon"
        if month in [10, 11]:
            return "Post-Monsoon"
        return "Winter"
    # Northern hemisphere generic
    if lat is None or lat >= 0:
        if month in [3, 4, 5]:
            return "Spring"
        if month in [6, 7, 8]:
            return "Summer"
        if month in [9, 10, 11]:
            return "Autumn"
        return "Winter"
    # Southern hemisphere
    if month in [3, 4, 5]:
        return "Autumn"
    if month in [6, 7, 8]:
        return "Winter"
    if month in [9, 10, 11]:
        return "Spring"
    return "Summer"


def get_disease_risks(season, temp_c, humidity, condition):
    risks = []
    if season == "Monsoon":
        risks = ["Dengue fever", "Malaria", "Typhoid", "Cholera", "Viral fever", "Leptospirosis"]
    elif season == "Winter":
        risks = ["Influenza", "Common cold", "Pneumonia", "Bronchitis", "Respiratory infections"]
    elif season == "Summer":
        if temp_c and temp_c > 35:
            risks = ["Heatstroke", "Heat exhaustion", "Dehydration", "Sunstroke", "Food poisoning"]
        else:
            risks = ["Dehydration", "Allergies", "Food poisoning"]
    elif season in ["Spring", "Post-Monsoon"]:
        risks = ["Allergies", "Hay fever", "Dengue", "Respiratory infections"]

    if condition and "Rain" in condition and "Waterborne diseases" not in risks:
        risks.append("Waterborne diseases")
    if humidity and humidity > 80 and "Fungal infections" not in risks:
        risks.append("Fungal infections")
    return risks


def build_context():
    now = time.time()
    if _cache["value"] and (now - _cache["ts"]) < _CACHE_TTL:
        return _cache["value"]

    location = get_user_location()
    if not location:
        return ""

    lat = location["lat"]
    lon = location["lon"]
    city = location["city"]
    region = location["region"]
    country = location["country"]

    season = get_season(lat, lon)
    weather = get_weather(lat, lon)

    lines = [
        "=== PATIENT ENVIRONMENTAL CONTEXT ===",
        f"Location: {city}, {region}, {country}",
        f"Season: {season}",
    ]

    temp_c = None
    humidity = None
    condition = None

    if weather:
        temp_c = weather["temp_c"]
        humidity = weather["humidity"]
        condition = weather["condition"]
        lines.append(f"Current Weather: {condition}, {temp_c}°C, Humidity: {humidity}%")

    risks = get_disease_risks(season, temp_c, humidity, condition)
    if risks:
        lines.append(f"Elevated Disease Risks This Season: {', '.join(risks)}")

    lines.append(
        "Use the above context to make your medical response more relevant "
        "to the patient's current environment and season."
    )
    lines.append("=====================================")

    result = "\n".join(lines)
    _cache["value"] = result
    _cache["ts"] = time.time()
    return result
