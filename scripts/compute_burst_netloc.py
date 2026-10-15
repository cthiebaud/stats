#!/usr/bin/env python3
"""Net new lines per burst -- added minus deleted, cloc-filtered, summed
across every repo in the project's group and every curated ref -- the
numerator for the "productivity" y-axis (net lines / working-day), replacing
commits/day on the chart entirely (2026-10-15).

Why net, not gross churn: Christophe's call -- lines added then deleted
again within the same burst are rework, not productive output, and should
be discarded from a productivity measure, not counted twice. `added -
deleted` cancels that out automatically with data this pipeline already
collects (commit_changes() in lines_changed_by_day.py already tracks both
components per commit) -- no new git operations needed. Known limitation:
this also nets out genuine deletions of code that PREDATES the burst (real
cleanup/simplification, not rework of this burst's own work) -- a cheap v1
approximation, not precise line-provenance tracking. Revisit with
diff-hunk-level blame if this proxy looks wrong on real data.

Run with: python3 scripts/compute_burst_netloc.py
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"
CLONES_DIR = ROOT / "clones"
BURSTS_JSON = Path(__file__).parent / "bursts.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lines_changed_by_day import commit_changes, cloc_allowed_tokens  # noqa: E402
from manual_excludes import MANUAL_EXCLUDES  # noqa: E402
from repo_refs import refs_for  # noqa: E402


def load_groups():
    data = yaml.safe_load(REPOS_YAML.read_text())
    return {g["name"]: g for g in data["groups"] if g["status"] == "include"}


def day_bounds_epoch(start_str, end_str):
    import datetime
    y, m, d = (int(x) for x in start_str.split("-"))
    start = int(datetime.datetime(y, m, d, 0, 0, 0, tzinfo=datetime.timezone.utc).timestamp())
    y, m, d = (int(x) for x in end_str.split("-"))
    end = int(datetime.datetime(y, m, d, 23, 59, 59, tzinfo=datetime.timezone.utc).timestamp())
    return start, end


def main():
    groups = load_groups()
    bursts_by_project = json.loads(BURSTS_JSON.read_text())
    allowed_tokens = cloc_allowed_tokens()

    result = {}
    for project, bursts in bursts_by_project.items():
        group = groups[project]
        repo_entries = [(e["owner"], e["repo"]) for e in group["repos"]]

        # one full-history scan per repo, shared across all of this project's bursts
        changes_by_repo = {}
        for owner, repo in repo_entries:
            path = CLONES_DIR / project / owner / repo
            key = f"{owner}/{repo}"
            changes = {}
            for ref in refs_for(owner, repo):
                changes.update(commit_changes(path, ref, allowed_tokens, MANUAL_EXCLUDES.get(key, [])))
            changes_by_repo[key] = changes

        names = [project] if len(bursts) == 1 else [f"{project}{i+1}" for i in range(len(bursts))]
        for burst_name, burst in zip(names, bursts):
            lo, hi = day_bounds_epoch(burst["start"], burst["end"])
            net_total = 0
            for key, changes in changes_by_repo.items():
                for epoch, churn, net in changes.values():
                    if lo <= epoch <= hi:
                        net_total += net
            result[burst_name] = net_total
            active_days = burst["active_days"]
            print(f"  {burst_name:<20} net_lines={net_total:<8} active_days={active_days:<4} "
                  f"net_lines/day={net_total/active_days:.1f}")

    out_path = Path(__file__).parent / "burst_netloc.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
