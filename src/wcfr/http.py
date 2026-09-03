from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = "west-coast-fishing-report/0.1 (personal research; GitHub project)"


def get_bytes(url: str, attempts: int = 3, timeout: int = 30) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"request failed after {attempts} attempts: {url}") from last


def get_json(url: str):
    return json.loads(get_bytes(url).decode("utf-8"))
