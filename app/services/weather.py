import httpx
import os
from datetime import datetime
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

class QWeatherService:
    def __init__(self):
        self.api_key = os.getenv("QWEATHER_API_KEY")
        self.weather_url = os.getenv("QWEATHER_API_BASE")
        self.geo_url = os.getenv("QWEATHER_GEO_BASE")
    
    async def get_location_id(self, city_name: str) -> Optional[str]:
        url = self.geo_url
        params = {
            "location": city_name,
            "key": self.api_key,
            "number": 1
        }
    
        async with httpx.AsyncClient() as client:
            try:
                print(f"🔍 [GeoAPI] Requesting: {url} with params {params}")
                resp = await client.get(url, params=params)

                if resp.status_code != 200:
                    print(f"❌ GeoAPI HTTP Error: {resp.status_code}")
                    return None
                
                data = resp.json()
                if data.get("code") == "200" and data.get("location"):
                    city_id = data["location"][0]["id"]
                    print(f"✅ Found Location ID: {city_id}")
                    return city_id
                else:
                    print(f"⚠️ GeoAPI No Result: {data.get('code')}")
            except Exception as e:
                print(f"❌ GeoAPI Exception: {e}")
        return None
    
    async def get_weather_forecast(self, location_id: str, target_date: datetime) -> Dict:
        url = self.weather_url
        params = {"location": location_id, "key": self.api_key}
        today = datetime.now().date()
        target_day = target_date.date()
        days_diff = (target_day - today).days
        print(f"🌤️ [WeatherAPI] Requesting: {url} for Location: {location_id}")

        async with httpx.AsyncClient() as client:
            try:
                if 0 <= days_diff <= 2:
                    resp = await client.get(url, params=params)

                    if resp.status_code != 200:
                        print(f"❌ WeatherAPI HTTP Error: {resp.status_code}")
                        return {}
                    
                    data = resp.json()
                    if data.get("code") == "200":
                        target_str = target_day.strftime("%Y-%m-%d")
                        for day in data["daily"]:
                            if day["fxDate"] == target_str:
                                return {
                                    "temp_max": day["tempMax"],
                                    "temp_min": day["tempMin"],
                                    "text": day["textDay"],
                                    "wind": day["windDirDay"],
                                    "precip": day["precip"]
                                }
                        print(f"⚠️ Date {target_str} not found.")
                    else:
                        print(f"⚠️ WeatherAPI Error Code: {data.get('code')}")
                else:
                    print(f"⚠️ Date out of range (Only Today+2 days).")
            except Exception as e:
                print(f"❌ WeatherAPI Exception: {e}")

            return {}

weather_service = QWeatherService()