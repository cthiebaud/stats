#!/usr/bin/env python3
"""Per-repo, per-day lines-changed series for the mini-bar-chart-per-project
(sparkline) feature -- see PROMPT.md "Open / unfinished work" #1.

For every repo in an `include` group of repos.yaml, walks full history via
`git log --numstat`, sums added+deleted lines per commit restricted to files
that would pass the same cloc filter used for the LOC methodology
(--exclude-lang=SVG,JSON,YAML,CSV -- unambiguous by extension, so no need to
shell out to cloc per commit), then buckets by calendar day (UTC).

Run with: python3 scripts/lines_changed_by_day.py
"""
import fnmatch
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"
CLONES_DIR = ROOT / "clones"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manual_excludes import MANUAL_EXCLUDES  # noqa: E402
from repo_refs import refs_for  # noqa: E402

# XML added 2026-10-15: bwv543's MusicXML score files play the same "content,
# not code" role SVG already plays for every other bwv/ciaccona repo -- same
# exclusion principle, confirmed with Christophe. Also applied in
# gather_data.py's cloc call, for consistency.
EXCLUDED_LANGS = {"SVG", "JSON", "YAML", "CSV", "XML"}

NUMSTAT_RE = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")
LANG_LINE_RE = re.compile(r"^(.+?)\s{2,}\(([^)]+)\)\s*$")


def cloc_allowed_tokens():
    """Build the set of filename/extension tokens cloc recognizes as code,
    excluding the languages the LOC methodology already excludes. This is an
    allowlist (not a 4-extension blocklist) so non-code files that git's
    binary-detection heuristic fails to flag -- e.g. certain PDFs, which
    diffed as 165k 'lines' in one real commit -- are correctly excluded, same
    as cloc itself would exclude them (PDF isn't in cloc's language table)."""
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
    """numstat's path field is plain, or 'old => new' / 'a/{old => new}/b'
    when rename detection is on. Return the final (post-change) filename."""
    if " => " in path_field:
        pre, _, post = path_field.partition(" => ")
        if "{" in pre or "{" in path_field:
            # a/{old => new}/b.ext  ->  reconstruct the new side
            path_field = re.sub(r"\{[^{}]*=>\s*([^{}]*)\}", r"\1", path_field)
            return path_field
        return post
    return path_field


def is_counted(path_field, allowed_tokens, manual_exclude_globs):
    fname = target_filename(path_field)
    name = Path(fname).name.lower()
    ext = Path(name).suffix.lstrip(".")
    if not (name in allowed_tokens or ext in allowed_tokens):
        return False
    return not any(fnmatch.fnmatch(fname, pat) for pat in manual_exclude_globs)


def day_of(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d")


def commit_changes(path, ref, allowed_tokens, manual_exclude_globs):
    """{hash: (epoch, lines_changed)} for one ref's history, cloc-filtered."""
    out = subprocess.run(
        ["git", "-C", str(path), "log", ref, "--format=COMMIT\t%H\t%at", "--numstat"],
        capture_output=True, text=True,
    ).stdout

    changes = {}
    current_hash = None
    current_epoch = None
    for line in out.splitlines():
        if line.startswith("COMMIT\t"):
            _, h, t = line.split("\t")
            current_hash = h
            current_epoch = int(t)
            changes[current_hash] = (current_epoch, 0)
            continue
        if not line.strip() or current_hash is None:
            continue
        m = NUMSTAT_RE.match(line)
        if not m:
            continue
        added, deleted, path_field = m.groups()
        if added == "-" or deleted == "-":
            continue  # binary file, cloc wouldn't count it either
        if not is_counted(path_field, allowed_tokens, manual_exclude_globs):
            continue
        epoch, total = changes[current_hash]
        changes[current_hash] = (epoch, total + int(added) + int(deleted))

    return changes


def repo_daily_series(owner, repo, path, allowed_tokens, manual_exclude_globs):
    """{date: lines_changed} for one repo, across HEAD + any curated extra_refs,
    deduped by commit hash, cloc-filtered."""
    changes = {}
    for ref in refs_for(owner, repo):
        changes.update(commit_changes(path, ref, allowed_tokens, manual_exclude_globs))

    daily = defaultdict(int)
    for epoch, lines in changes.values():
        daily[day_of(epoch)] += lines

    return dict(sorted(daily.items()))


def main():
    data = yaml.safe_load(REPOS_YAML.read_text())
    groups = [g for g in data["groups"] if g["status"] == "include"]
    allowed_tokens = cloc_allowed_tokens()

    result = {}
    for group in groups:
        result[group["name"]] = {}
        for entry in group["repos"]:
            owner, repo = entry["owner"], entry["repo"]
            path = CLONES_DIR / group["name"] / owner / repo
            key = f"{owner}/{repo}"
            series = repo_daily_series(owner, repo, path, allowed_tokens, MANUAL_EXCLUDES.get(key, []))
            result[group["name"]][key] = series
            total = sum(series.values())
            print(f"  {group['name']:<20} {key:<45} days_with_activity={len(series):<5} total_lines_changed={total}")

    out_path = Path(__file__).parent / "lines_changed_by_day.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
