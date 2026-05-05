#!/usr/bin/env python3
"""Download and sync the shared research-agent prompt kernel.

The upstream repository owns reusable prompt assets. This project keeps
``prompts/meta/kernel-project.md`` local, so normal sync must preserve it and
then run project-local redeploy/audit checks before the agents are used.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_REMOTE = "git@github.com:t0m0h1r0/research-agent.git"
DEFAULT_FALLBACK = "https://github.com/t0m0h1r0/research-agent.git"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def clone(remote: str, destination: Path) -> None:
    run(["git", "clone", "--depth", "1", remote, str(destination)])


def fetch_upstream(remote: str, fallback: str | None, keep_checkout: Path | None) -> Path:
    if keep_checkout is not None:
        if keep_checkout.exists():
            run(["git", "pull", "--ff-only"], cwd=keep_checkout)
            return keep_checkout
        keep_checkout.parent.mkdir(parents=True, exist_ok=True)
        try:
            clone(remote, keep_checkout)
        except subprocess.CalledProcessError:
            if not fallback:
                raise
            clone(fallback, keep_checkout)
        return keep_checkout

    tmp = Path(tempfile.mkdtemp(prefix="research-agent-"))
    checkout = tmp / "repo"
    try:
        clone(remote, checkout)
    except subprocess.CalledProcessError:
        if not fallback:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        clone(fallback, checkout)
    return checkout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=".", help="Project repository root")
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--fallback", default=DEFAULT_FALLBACK)
    parser.add_argument(
        "--groups",
        default="kernel,skills,agents-codex,agents-claude",
        help="Comma-separated upstream groups passed to scripts/sync_to_project.py",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--keep-checkout",
        type=Path,
        help="Optional reusable checkout path for the upstream repository",
    )
    args = parser.parse_args()

    target = Path(args.target).resolve()
    checkout = fetch_upstream(args.remote, args.fallback, args.keep_checkout)
    sync_script = checkout / "scripts" / "sync_to_project.py"
    if not sync_script.exists():
        raise SystemExit(f"missing upstream sync script: {sync_script}")

    cmd = [sys.executable, str(sync_script), "--target", str(target), "--groups", args.groups]
    if args.dry_run:
        cmd.append("--dry-run")
    run(cmd)

    print()
    print("Next: run project-local redeploy/audit checks.")
    print("Guard: prompts/meta/kernel-project.md must remain unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
