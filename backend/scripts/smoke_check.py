"""Manual end-to-end check against a running Twemp API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

BASE = "http://127.0.0.1:8000"

INCIDENT: dict[str, Any] = {
    "title": "Checkout latency surge across EU region",
    "description": (
        "Checkout p95 latency climbed from 420 ms to 8.4 s after the payment-router deployment."
    ),
    "service": "payment-router",
    "severity": "SEV-1",
    "region": "eu-central",
    "signals": ["p95 latency 8.4 s", "HTTP 5xx rate 18%"],
}


def call(method: str, path: str, payload: Any = None) -> tuple[int, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main() -> None:
    print("health:", call("GET", "/health"))

    status, run = call("POST", "/api/workflows", INCIDENT)
    print("create:", status, run["status"], run["phase"])
    print("  agents:", run["metrics"]["agentsTotal"], "handoffs:", run["metrics"]["handoffs"])
    print("  findings:", len(run["findings"]), "reports:", len(run["teamReports"]))
    print("  remediation before approval:", any(e["type"] == "remediation" for e in run["events"]))
    print("  startedAt:", run["startedAt"])
    print("  planRiskLevel:", run["plan"]["riskLevel"])

    status, fetched = call("GET", f"/api/workflows/{run['id']}")
    print("get:", status, "same run:", fetched["id"] == run["id"])

    status, done = call(
        "POST",
        f"/api/workflows/{run['id']}/decision",
        {"decision": "approve", "reviewer": "Primary on-call", "note": "Reviewed"},
    )
    print("approve:", status, done["status"], done["verification"]["status"])
    print("  followUps:", len(done["outcome"]["followUps"]))

    status, replay = call(
        "POST",
        f"/api/workflows/{run['id']}/decision",
        {"decision": "approve", "reviewer": "Primary on-call"},
    )
    print("replay:", status, replay["error"])

    status, invalid = call("POST", "/api/workflows", {**INCIDENT, "severity": "SEV-9"})
    print("invalid:", status, invalid["error"], invalid["details"][0])

    status, missing = call("GET", "/api/workflows/INC-UNKNOWN")
    print("missing:", status, missing["error"])


if __name__ == "__main__":
    main()
