#!/usr/bin/env python3
"""Diagnostic: per repo, the top files by total lines-changed (added+deleted,
summed across all history), restricted to the same cloc-allowlist filter used
by lines_changed_by_day.py. Used to spot vendor libraries / generated data
dumps that the language-level filter can't catch, so they can be manually
excluded by path.
"""
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"
CLONES_DIR = ROOT / "clones"

EXCLUDED_LANGS = {"SVG", "JSON", "YAML", "CSV"}
NUMSTAT_RE = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")
LANG_LINE_RE = re.compile(r"^(.+?)\s{2,}\(([^)]+)\)\s*$")


def cloc_allowed_tokens():
    out = subprocess.run(["cloc", "--show-lang"], capture_output=True, text=True).stdout
    tokens = set()
    for line in out.splitlines():
        m = LANG_LINE_RE.match(line)
        if not m:
            continue
        lang, ext_list = m.group(1).strip(), m.group(2)
        if lang in EXCLUDED_LANGS:
            continue
        for tok in ext_list.split(","):
            tokens.add(tok.strip().lower())
    return tokens


def target_filename(path_field):
    if " => " in path_field:
        pre, _, post = path_field.partition(" => ")
        if "{" in pre or "{" in path_field:
            path_field = re.sub(r"\{[^{}]*=>\s*([^{}]*)\}", r"\1", path_field)
            return path_field
        return post
    return path_field


def is_counted(path_field, allowed_tokens):
    name = Path(target_filename(path_field)).name.lower()
    ext = Path(name).suffix.lstrip(".")
    return name in allowed_tokens or ext in allowed_tokens


def per_file_totals(path, allowed_tokens):
    out = subprocess.run(
        ["git", "-C", str(path), "log", "--format=COMMIT%x09%H", "--numstat"],
        capture_output=True, text=True,
    ).stdout
    totals = defaultdict(int)
    for line in out.splitlines():
        if line.startswith("COMMIT\t") or not line.strip():
            continue
        m = NUMSTAT_RE.match(line)
        if not m:
            continue
        added, deleted, path_field = m.groups()
        if added == "-" or deleted == "-":
            continue
        if not is_counted(path_field, allowed_tokens):
            continue
        fname = target_filename(path_field)
        totals[fname] += int(added) + int(deleted)
    return totals


def main():
    data = yaml.safe_load(REPOS_YAML.read_text())
    groups = [g for g in data["groups"] if g["status"] == "include"]
    allowed_tokens = cloc_allowed_tokens()

    for group in groups:
        for entry in group["repos"]:
            owner, repo = entry["owner"], entry["repo"]
            path = CLONES_DIR / group["name"] / owner / repo
            totals = per_file_totals(path, allowed_tokens)
            top = sorted(totals.items(), key=lambda kv: -kv[1])[:8]
            top = [(f, n) for f, n in top if n >= 500]
            if not top:
                continue
            print(f"\n=== {group['name']}  {owner}/{repo} ===")
            for fname, n in top:
                print(f"  {n:>8}  {fname}")


if __name__ == "__main__":
    main()
