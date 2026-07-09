import hashlib
import json
import time
from core.logger import log_info, log_error
from core.cache import cache_get, cache_set
from services.api import _SESSION, init_session

CACHE_KEY = "google_fonts_cache"
CACHE_TTL = 86400

async def get_fonts_data():
    cached = await cache_get(CACHE_KEY)
    if cached:
        return cached

    try:
        try:
            from core.secrets import GOOGLE_FONTS_API_KEY
            api_key = GOOGLE_FONTS_API_KEY
        except ImportError:
            api_key = None
        
        if not api_key:
            log_error("GOOGLE_FONTS_API_KEY is not defined in core/secrets.py!")
            raise Exception("Google Fonts API key not configured")

        log_info("Fetching Google Fonts list from Google API...")
        if not _SESSION:
            await init_session()

        url = f"https://www.googleapis.com/webfonts/v1/webfonts?key={api_key}"
        async with _SESSION.get(url) as response:
            if response.status != 200:
                log_error(f"Failed to fetch Google Fonts. Status: {response.status}")
                raise Exception(f"HTTP Status {response.status}")
            
            data = await response.json()
            items = data.get("items", [])
            
            fonts_dict = {}
            for item in items:
                family = item.get("family")
                files = item.get("files", {})
                if not family or not files:
                    continue
                
                font_url = files.get("regular")
                if not font_url:
                    font_url = next(iter(files.values())) if files else None
                
                if font_url:
                    if font_url.startswith("http://"):
                        font_url = "https://" + font_url[7:]
                    fonts_dict[family] = font_url
            
            serialized_fonts = json.dumps(fonts_dict, sort_keys=True)
            hash_val = hashlib.md5(serialized_fonts.encode('utf-8')).hexdigest()
            
            cache_data = {
                "hash": hash_val,
                "fonts": fonts_dict
            }
            
            await cache_set(CACHE_KEY, cache_data, ttl=CACHE_TTL)
            log_info(f"Successfully cached {len(fonts_dict)} Google Fonts with hash {hash_val}")
            return cache_data
            
    except Exception as e:
        log_error(f"Error fetching Google Fonts: {e}")
        
        try:
            import core.cache
            entry = core.cache._DATA_CACHE.get(CACHE_KEY)
            if entry:
                stale_data = entry[1]
                await cache_set(CACHE_KEY, stale_data, ttl=3600)
                log_info("Google Fonts fetch failed. Served stale cache extended by 1 hour.")
                return stale_data
        except Exception as cache_err:
            log_error(f"Failed to retrieve stale cache: {cache_err}")
            
        return None
