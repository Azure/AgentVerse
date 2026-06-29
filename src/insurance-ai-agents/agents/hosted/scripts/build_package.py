"""Build the Foundry direct-code deployment zip (flat root: main.py + requirements.txt + agents/).

Usage:  python build_package.py [output_zip_path]
Defaults to %TEMP%/insurance-agent-code.zip (or /tmp on Unix). Prints the path and SHA-256.

The zip is a *build artifact* — it is not committed (see .gitignore). The committed
deployment descriptor is .foundry/direct-code/metadata.json.
"""
import hashlib
import os
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

# scripts/ -> hosted/ -> agents/ -> <repo root>
REPO = Path(__file__).resolve().parents[3]

MAIN_PY = (
    "import os\n"
    "from agents.hosted.app import app\n"
    "\n"
    "if __name__ == \"__main__\":\n"
    "    app.run(host=\"0.0.0.0\", port=int(os.environ.get(\"PORT\", \"8088\")))\n"
)

# Only the subpackages process_claim needs. voice/ and content_understanding/ are excluded.
INCLUDE_SUBPKGS = ["orchestrator", "claims-intake", "risk-assessment", "compliance", "shared", "hosted"]
EXCLUDE_PARTS = {"__pycache__", ".venv", ".venv-foundry", ".venv-hosted", ".foundry"}
EXCLUDE_NAMES = {".env", ".DS_Store"}


def build(zip_path: Path) -> str:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("main.py", MAIN_PY)
        zf.writestr("requirements.txt", (REPO / "agents" / "hosted" / "requirements.txt").read_text(encoding="utf-8"))
        zf.write(REPO / "agents" / "__init__.py", "agents/__init__.py")
        for sub in INCLUDE_SUBPKGS:
            for p in (REPO / "agents" / sub).rglob("*.py"):
                if any(part in EXCLUDE_PARTS for part in p.parts) or p.name in EXCLUDE_NAMES:
                    continue
                zf.write(p, p.relative_to(REPO).as_posix())
    return hashlib.sha256(zip_path.read_bytes()).hexdigest()


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "insurance-agent-code.zip"
    sha = build(out)
    print(str(out))
    print(sha)
