import httpx

class LocationService:
    def __init__(self):
        self.api_url = "http://ip-api.com/json"
    
    async def get_city_from_ip(self, ip_address: str) -> str:
        """
        输入IP，返回城市名(英文，如Zhengzhou)
        """

        if ip_address in ["127.0.0.1", "localhost", "0.0.0.0", "::1"] or ip_address.startswith("172.") or ip_address.startswith("192.168."):
            print(f"🌍 [Location] Local IP ({ip_address}) detected. Using default fallback 'Beijing'.")
            return "Beijing"
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.api_url}/{ip_address}?lang=en"
                resp = await client.get(url, timeout=5.0)
                data = resp.json()

                if data['status'] == 'success':
                    city = data['city']
                    print(f"🌍 [Location] IP {ip_address} -> {city}")
                    return city
                else:
                    print(f"⚠️ [Location] IP lookup failed: {data.get('message')}")
        except Exception as e:
            print(f"❌ [Location] Service Error: {e}")
        
        return None

location_service = LocationService()