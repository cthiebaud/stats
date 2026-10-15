#!/usr/bin/env python3
"""Clone every repo belonging to an `include` group in repos.yaml into
clones/<group>/<owner>/<repo> -- a fresh, independent clone per repo, even
when a working copy already exists elsewhere on this machine (deliberate,
per Christophe's choice: no symlinking into existing clones)."""

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"
CLONES_DIR = ROOT / "clones"


def main():
    data = yaml.safe_load(REPOS_YAML.read_text())
    groups = [g for g in data["groups"] if g["status"] == "include"]

    print(f"{len(groups)} included groups to clone.\n")

    cloned, skipped, failed = 0, 0, []

    for group in groups:
        for entry in group["repos"]:
            owner, repo = entry["owner"], entry["repo"]
            dest = CLONES_DIR / group["name"] / owner / repo

            if dest.exists():
                print(f"  SKIP  {dest.relative_to(ROOT)} (already exists)")
                skipped += 1
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://github.com/{owner}/{repo}.git"
            print(f"  CLONE {url} -> {dest.relative_to(ROOT)}")
            result = subprocess.run(
                ["git", "clone", "--quiet", url, str(dest)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"    FAILED: {result.stderr.strip()}")
                failed.append((owner, repo, result.stderr.strip()))
            else:
                cloned += 1

    print(f"\nDone. Cloned {cloned}, skipped {skipped}, failed {len(failed)}.")
    if failed:
        print("\nFailures:")
        for owner, repo, err in failed:
            print(f"  {owner}/{repo}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
