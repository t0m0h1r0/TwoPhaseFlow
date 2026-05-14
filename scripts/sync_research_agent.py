#!/usr/bin/env python3
"""Update the research-agent submodule that backs prompts/meta.

The shared kernel now lives as a Git submodule at ``prompts/meta``. This helper
initializes the submodule when needed and advances it to the configured remote
HEAD; callers should review and commit the resulting gitlink change.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


DEFAULT_SUBMODULE_PATH = "prompts/meta"


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def capture(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=".", help="Project repository root")
    parser.add_argument("--path", default=DEFAULT_SUBMODULE_PATH, help="Submodule path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--remote", help=argparse.SUPPRESS)
    parser.add_argument("--fallback", help=argparse.SUPPRESS)
    parser.add_argument("--groups", help=argparse.SUPPRESS)
    parser.add_argument("--keep-checkout", help=argparse.SUPPRESS)
    args = parser.parse_args()

    target = Path(args.target).resolve()
    submodule_path = args.path
    submodule = target / submodule_path

    if not (target / ".gitmodules").exists():
        raise SystemExit("missing .gitmodules; research-agent submodule is not configured")

    if args.dry_run:
        run(["git", "submodule", "status", submodule_path], cwd=target)
        print(f"Dry run: would update submodule {submodule_path}")
        return 0

    run(["git", "submodule", "update", "--init", submodule_path], cwd=target)
    run(["git", "submodule", "update", "--remote", submodule_path], cwd=target)
    revision = capture(["git", "-C", str(submodule), "rev-parse", "HEAD"], cwd=target)

    print()
    print(f"{submodule_path} is at {revision}.")
    print("Next: review the submodule diff, commit the gitlink, then redeploy/audit generated prompts if kernel content changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
