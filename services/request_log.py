import time
import os
import json
from collections import deque
from typing import List, Optional

MAX_ENTRIES = 100
MAX_BODY_PREVIEW = 200
MAX_HEADER_VALUE = 160
MAX_HEADERS = 24
MAX_QUERY_VALUE = 120
LOG_FILE = "data/request_log.json"


class RequestLog:
    def __init__(self, max_entries: int = MAX_ENTRIES):
        self.entries: deque = deque(maxlen=max_entries)
        self._load()

    def _load(self):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.entries.extend(data)
        except Exception:
            pass

    def _save(self):
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self.entries), f, indent=4, default=str)
        except Exception:
            pass

    def add(
        self,
        ip: str,
        method: str,
        path: str,
        query: str,
        status: int,
        body_preview: str = "",
        details: Optional[dict] = None,
    ):
        self.entries.append({
            "id": f"{int(time.time())}-{len(self.entries)}",
            "ts": int(time.time()),
            "ip": ip,
            "method": method,
            "path": path,
            "query": sanitize_query(query or ""),
            "status": status,
            "body": sanitize_body_preview(body_preview or "", MAX_BODY_PREVIEW),
            "details": details or {},
        })
        self._save()

    def get_recent(self, limit: Optional[int] = None, ip_filter: Optional[str] = None) -> List[dict]:
        items = list(self.entries)
        items.reverse()
        if ip_filter:
            ip_filter = ip_filter.strip()
            items = [e for e in items if e["ip"] == ip_filter]
        if limit:
            items = items[:limit]
        return items

    def clear(self):
        self.entries.clear()
        self._save()


request_log = RequestLog()


def sanitize_text(value: str, max_len: int) -> str:
    text = str(value or "").replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text


def sanitize_query(query: str) -> str:
    return sanitize_text(query, MAX_QUERY_VALUE)


def sanitize_headers(headers) -> dict:
    safe = {}
    for index, (key, value) in enumerate(headers.items()):
        if index >= MAX_HEADERS:
            safe["..."] = f"{len(headers) - MAX_HEADERS} more headers omitted"
            break
        safe[key] = sanitize_text(value, MAX_HEADER_VALUE)
    return safe


def sanitize_body_preview(value: str, max_len: int) -> str:
    return sanitize_text(value, max_len)
