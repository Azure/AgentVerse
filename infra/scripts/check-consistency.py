#!/usr/bin/env python3
"""Check consistency between the catalog and the Terraform demo topology.

Two independent sources describe a demo:
  * presentation metadata -> src/<demo>/agentverse.yaml  (aggregated in catalog.json)
  * deployment topology    -> infra/demos.auto.tfvars      (the `demos` map)
They are linked by the demo id (catalog `name` == demos map key). This script
flags drift: demos deployed without metadata, or metadata without a topology
entry. It is dependency-light (regex-based) so it runs anywhere Python does.

Usage (from repo root):
    python infra/scripts/check-consistency.py
Exit code 1 on any inconsistency, 0 otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "src" / "catalog.json"
TFVARS_CANDIDATES = [
    REPO_ROOT / "infra" / "demos.auto.tfvars",
    REPO_ROOT / "infra" / "demos.auto.tfvars.example",
]


def catalog_ids() -> set[str]:
    if not CATALOG.exists():
        print(f"WARN: {CATALOG} not found. Run build_catalog.py --write first.")
        return set()
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {d["name"] for d in data.get("demos", [])}


def tfvars_ids(path: Path) -> set[str]:
    """Extract the top-level keys of the `demos = { ... }` map."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"demos\s*=\s*{", text)
    if not m:
        return set()
    # Keys look like:  <id> = {   at brace depth 1.
    ids: set[str] = set()
    depth = 0
    for line in text[m.end() - 1:].splitlines():
        depth += line.count("{") - line.count("}")
        km = re.match(r"\s*([A-Za-z0-9_-]+)\s*=\s*{", line)
        if km and depth == 2:
            ids.add(km.group(1))
        if depth <= 0:
            break
    return ids


def main() -> int:
    tfvars = next((p for p in TFVARS_CANDIDATES if p.exists()), None)
    if tfvars is None:
        print("No demos.auto.tfvars(.example) found; nothing to cross-check.")
        return 0

    cat = catalog_ids()
    topo = tfvars_ids(tfvars)
    print(f"catalog demos ({len(cat)}): {sorted(cat)}")
    print(f"topology demos ({len(topo)}) from {tfvars.name}: {sorted(topo)}")

    problems = []
    for missing in sorted(topo - cat):
        problems.append(f"'{missing}' has a deployment topology but no catalog manifest (agentverse.yaml).")
    for missing in sorted(cat - topo):
        problems.append(f"'{missing}' has catalog metadata but no deployment topology entry.")

    if problems:
        print("\nInconsistencies:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nOK: catalog and topology are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
