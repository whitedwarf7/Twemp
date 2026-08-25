"""Regenerate the shared contract fixtures consumed by the backend and frontend test suites.

Usage:
    python scripts/export_contract_fixtures.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.workflow.demo_provider import DemoAgentProvider  # noqa: E402
from app.workflow.engine import decide_workflow, start_workflow  # noqa: E402
from app.workflow.schemas import DEFAULT_INCIDENT, ApprovalDecision  # noqa: E402

FIXTURE_DIR = BACKEND_ROOT.parent / "contract-fixtures"

# Timestamps and run ids are replaced so the committed fixtures stay byte-stable.
FIXED_RUN_ID = "INC-FIXTURE"
FIXED_TIMESTAMP = "2026-08-25T06:58:35.536Z"


def normalize(node: Any) -> Any:
    """Replace generated ids and timestamps with stable values."""
    if isinstance(node, dict):
        return {key: normalize(value) for key, value in node.items()}
    if isinstance(node, list):
        return [normalize(item) for item in node]
    if isinstance(node, str):
        if node.startswith("INC-") and node != FIXED_RUN_ID:
            _, _, tail = node.partition("-")
            _, _, remainder = tail.partition("-")
            return f"{FIXED_RUN_ID}-{remainder}" if remainder else FIXED_RUN_ID
        if len(node) == 24 and node.endswith("Z") and node[4] == "-":
            return FIXED_TIMESTAMP
    return node


async def build_fixtures() -> dict[str, Any]:
    provider = DemoAgentProvider()
    pending = await start_workflow(DEFAULT_INCIDENT, provider)
    completed = await decide_workflow(
        pending,
        ApprovalDecision(decision="approve", reviewer="Primary on-call", note="Reviewed"),
        provider,
    )
    rejected = await decide_workflow(
        pending,
        ApprovalDecision(decision="reject", reviewer="Incident commander", note="Too broad"),
        provider,
    )
    return {
        "awaiting-approval-run": pending.model_dump(mode="json", by_alias=True),
        "completed-run": completed.model_dump(mode="json", by_alias=True),
        "rejected-run": rejected.model_dump(mode="json", by_alias=True),
    }


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in asyncio.run(build_fixtures()).items():
        target = FIXTURE_DIR / f"{name}.json"
        target.write_text(json.dumps(normalize(payload), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
