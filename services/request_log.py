import time
from collections import deque
from typing import List, Optional

MAX_ENTRIES = 30
MAX_BODY_PREVIEW = 200


class RequestLog:
    def __init__(self, max_entries: int = MAX_ENTRIES):
        self.entries: deque = deque(maxlen=max_entries)

    def add(self, ip: str, method: str, path: str, query: str, status: int, body_preview: str = ""):
        self.entries.append({
            "ts": int(time.time()),
            "ip": ip,
            "method": method,
            "path": path,
            "query": query or "",
            "status": status,
            "body": (body_preview or "")[:MAX_BODY_PREVIEW],
        })

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


request_log = RequestLog()
