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
PROJECT_PROFILE = "kernel-project.md"


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def capture(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def submodule_status_except_project(target: Path, submodule: Path) -> str:
    status = capture(["git", "-C", str(submodule), "status", "--short"], cwd=target)
    lines = [line for line in status.splitlines() if line.strip() and not line.endswith(f" {PROJECT_PROFILE}")]
    return "\n".join(lines)


def preserve_project_profile(target: Path, submodule: Path) -> str | None:
    project_profile = submodule / PROJECT_PROFILE
    if not project_profile.exists():
        return None
    return project_profile.read_text(encoding="utf-8")


def restore_project_profile(submodule: Path, content: str | None) -> None:
    if content is None:
        return
    (submodule / PROJECT_PROFILE).write_text(content, encoding="utf-8")


def ensure_other_submodule_files_clean(target: Path, submodule: Path) -> None:
    status = submodule_status_except_project(target, submodule)
    if status:
        raise SystemExit(
            "Refusing to sync prompts/meta: the submodule has local changes outside kernel-project.md.\n"
            "Commit/stash those changes before syncing:\n"
            f"{status}"
        )


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
        if submodule.exists():
            ensure_other_submodule_files_clean(target, submodule)
        print(f"Dry run: would update submodule {submodule_path}")
        print(f"Project-specific profile {submodule_path}/{PROJECT_PROFILE} would be preserved across sync.")
        return 0

    run(["git", "submodule", "update", "--init", submodule_path], cwd=target)
    ensure_other_submodule_files_clean(target, submodule)
    project_profile = preserve_project_profile(target, submodule)
    if project_profile is not None:
        run(["git", "-C", str(submodule), "restore", "--", PROJECT_PROFILE], cwd=target)
    run(["git", "submodule", "update", "--remote", submodule_path], cwd=target)
    restore_project_profile(submodule, project_profile)
    revision = capture(["git", "-C", str(submodule), "rev-parse", "HEAD"], cwd=target)

    print()
    print(f"{submodule_path} is at {revision}.")
    print(f"Project-specific profile {submodule_path}/{PROJECT_PROFILE} was preserved across sync.")
    print("Next: review the submodule diff, commit the gitlink, then redeploy/audit generated prompts if kernel content changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
