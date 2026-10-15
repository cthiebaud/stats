#!/usr/bin/env python3
"""For every included repo, check every non-default branch for commits NOT
reachable from the default branch -- real work our pipeline (which only
ever reads the checked-out default branch) has been silently missing.
Dependabot branches and gh-pages are flagged separately (very likely noise:
bot-authored dependency bumps that are never merged; auto-generated build
output) rather than auto-excluded, so they can be eyeballed too.

Run with: python3 scripts/audit_hidden_branches.py
"""
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"
CLONES_DIR = ROOT / "clones"


def default_branch(path):
    out = subprocess.run(["git", "-C", str(path), "symbolic-ref", "refs/remotes/origin/HEAD"],
                          capture_output=True, text=True).stdout.strip()
    return out.replace("refs/remotes/", "") if out else None


def branches(path):
    out = subprocess.run(["git", "-C", str(path), "branch", "-a"], capture_output=True, text=True).stdout
    return [l.strip().lstrip("* ") for l in out.splitlines() if l.strip()]


def unique_commits(path, default, branch):
    out = subprocess.run(["git", "-C", str(path), "log", f"{default}..{branch}", "--format=%H %at %an %s"],
                          capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if l.strip()]


groups = {g["name"]: g for g in yaml.safe_load(REPOS_YAML.read_text())["groups"] if g["status"] == "include"}

for gname, group in groups.items():
    for e in group["repos"]:
        path = CLONES_DIR / gname / e["owner"] / e["repo"]
        default = default_branch(path)
        if not default:
            continue
        for b in branches(path):
            if b in ("HEAD", default) or "HEAD ->" in b:
                continue
            uniq = unique_commits(path, default, b)
            if not uniq:
                continue
            kind = ""
            if "dependabot" in b:
                kind = "[DEPENDABOT -- likely bot noise]"
            elif b.endswith("gh-pages"):
                kind = "[GH-PAGES -- likely build output]"
            print(f"\n{gname}/{e['owner']}/{e['repo']}  branch={b}  {kind}")
            print(f"  {len(uniq)} commits not reachable from {default}")
            for line in uniq[:3]:
                print(f"    {line}")
            if len(uniq) > 3:
                print(f"    ... and {len(uniq) - 3} more")
