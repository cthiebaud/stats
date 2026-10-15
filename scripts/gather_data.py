"""
Data-gathering pipeline for the ai-dev-efficiency chart (index.html).

Sources every project's repo list from repos.yaml's `include` groups and
reads them from clones/<group>/<owner>/<repo> (fresh, independent clones --
see scripts/clone_repos.py). This replaced the earlier hand-maintained
ENTRIES dict pointing at ~/github.com/<owner>/<repo>, which predated the
full repo-inventory audit and had fallen out of sync with repos.yaml.

Computes, per project (group):
  - active-days lifespan (gap-clustered, immune to arbitrary idle-gap length)
  - commit count
  - LOC (via cloc, excluding SVG/JSON/YAML/CSV/XML -- same allowlist logic
    used by lines_changed_by_day.py; XML added because bwv543's MusicXML
    files play the same "content, not code" role SVG already does elsewhere)
  - calendar start/end (YYYY-MM, from actual commit history)

aiPct is NOT computed here -- it comes from ad hoc disclosure tool runs per
group (see PROMPT.md) and is hand-entered into index.html's `data` array.
(The subjective 1-5 "scope" rating this docstring used to mention was
dropped entirely once the chart moved from one row per project to one row
per gap-clustered burst, 2026-10-15 -- see PROMPT.md. There's no sane
per-burst equivalent of a whole-project scope rating.)

This script's project-level rollups (summary.json) are NOT what the chart's
`data` array is built from any more either -- that's now
compute_bursts.py + compute_burst_loc.py, which split each project's
history into bursts first. This script is kept for the coarser project-level
view it still produces (and as the reference LOC/cloc-filter implementation
the burst scripts import from).

Run with: python3 scripts/gather_data.py
"""
import json
import re
import subprocess
import sys
import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
REPOS_YAML = PROJECT_ROOT / "repos.yaml"
CLONES_DIR = PROJECT_ROOT / "clones"

sys.path.insert(0, str(ROOT))
from manual_excludes import MANUAL_EXCLUDES  # noqa: E402

LOC_EXCLUDE_LANGS = "SVG,JSON,YAML,CSV,XML"


def glob_to_regex(pattern):
    # (^|/) prefix tolerance: cloc's --fullpath reports paths as "./a/b.ext"
    # when scanning a directory directly, not just "a/b.ext".
    return r"(^|/)" + re.escape(pattern).replace(r"\*", ".*") + "$"


def load_groups():
    data = yaml.safe_load(REPOS_YAML.read_text())
    return [g for g in data["groups"] if g["status"] == "include"]


def repo_paths(group):
    return [CLONES_DIR / group["name"] / e["owner"] / e["repo"] for e in group["repos"]]


def get_epochs(paths):
    epochs = {}
    for path in paths:
        out = subprocess.run(["git", "-C", str(path), "log", "--format=%H %at"],
                              capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.split(" ")
            if len(parts) == 2:
                h, t = parts
                epochs[h] = int(t)
    return sorted(epochs.values())


def active_days(epochs, gap_days=120):
    """Sum each gap-clustered episode's own span - not the full outer range,
    not just the largest cluster. Immune to arbitrary choice of gap_days."""
    if len(epochs) <= 1:
        return 1.0
    gap_seconds = gap_days * 86400
    clusters = [[epochs[0]]]
    for e in epochs[1:]:
        if e - clusters[-1][-1] > gap_seconds:
            clusters.append([e])
        else:
            clusters[-1].append(e)
    total = sum((c[-1] - c[0]) / 86400 for c in clusters)
    return max(1.0, total)


def loc_for(group):
    # Scans the checked-out working tree directly (not `cloc --git HEAD`):
    # cloc's --fullpath is silently ineffective in --git mode (confirmed by
    # testing -- basename-only matching works there, full-path matching does
    # not), so --git mode can't apply the manual vendor/data-dump excludes.
    # Our clones are plain working-tree checkouts already on HEAD, so a
    # direct directory scan is equivalent and --fullpath works correctly.
    total = 0
    for entry in group["repos"]:
        owner, repo = entry["owner"], entry["repo"]
        path = CLONES_DIR / group["name"] / owner / repo
        cmd = ["cloc", ".", f"--exclude-lang={LOC_EXCLUDE_LANGS}", "--json"]
        patterns = MANUAL_EXCLUDES.get(f"{owner}/{repo}")
        if patterns:
            cmd += ["--fullpath", "--not-match-f=" + "(" + "|".join(glob_to_regex(p) for p in patterns) + ")"]
        out = subprocess.run(cmd, capture_output=True, text=True, cwd=path).stdout
        try:
            d = json.loads(out)
        except json.JSONDecodeError:
            continue
        total += d.get("SUM", {}).get("code", 0)
    return total


def fmt(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m")


if __name__ == "__main__":
    groups = load_groups()
    summary = []
    for group in groups:
        name = group["name"]
        paths = repo_paths(group)
        epochs = get_epochs(paths)
        if not epochs:
            print(f"{name:<22} NO COMMITS FOUND -- skipping")
            continue
        days = round(active_days(epochs), 1)
        commits = len(epochs)
        code = loc_for(group)
        summary.append({
            "name": name,
            "start": fmt(epochs[0]),
            "end": fmt(epochs[-1]),
            "days": days,
            "commits": commits,
            "loc": code,
        })
        print(f"{name:<22} {fmt(epochs[0])} -> {fmt(epochs[-1])}  days={days:<8} commits={commits:<6} loc={code}")

    with open(ROOT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nWrote scripts/summary.json")
