from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def send(report: Path, subject: str) -> dict:
    url = os.environ.get("APPS_SCRIPT_WEB_APP_URL")
    token = os.environ.get("FISHING_WEBHOOK_TOKEN")
    if not url or not token:
        raise RuntimeError("APPS_SCRIPT_WEB_APP_URL and FISHING_WEBHOOK_TOKEN are required")

    body = json.dumps({
        "token": token,
        "subject": subject,
        "html": report.read_text(encoding="utf-8"),
    }).encode("utf-8")
    request = Request(url, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": "west-coast-fishing-report/0.2",
    })
    with urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError("Apps Script mail gateway failed: " + result.get("error", "unknown error"))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--subject", required=True)
    args = parser.parse_args()
    print(json.dumps(send(args.report, args.subject)))


if __name__ == "__main__":
    main()
