#!/usr/bin/env python3
"""Split each project's commit history into bursts: gap-clustered episodes of
genuine activity, same clustering rule as gather_data.py's active_days() (120-
day gap threshold) but keeping each cluster as its own row instead of summing
their spans into one project-level total.

Uses real commit epochs (git log, not the cloc-filtered dailySeries), since a
day with only non-code changes should still count as "the burst is alive" --
narrower than what the sparkline trail shows.

This is step 1 only: burst boundaries + commit-based stats (commits,
active_days, commits/day). Does NOT yet checkout historical commits or run
cloc for the end-of-burst LOC circle -- that's a separate, heavier follow-up
once the boundaries themselves are confirmed.

Run with: python3 scripts/compute_bursts.py
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_refs import refs_for  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"
CLONES_DIR = ROOT / "clones"

GAP_DAYS = 120
# A cluster spanning exactly one calendar day is a single sitting (a lone fix,
# a redirect update), not a coding campaign -- dropped entirely, not merged.
# Confirmed on real data: every current single-day cluster has 1-3 commits
# (covid1/3, parimagine2, sangiovannilipioni2, ciaccona2, music2); the
# smallest *kept* multi-day burst is ciaccona4 at 27.2 active_days, so this
# is a real gap in the distribution, not an arbitrary tuned threshold.
MIN_ACTIVE_DAYS = 1.0


def load_groups():
    data = yaml.safe_load(REPOS_YAML.read_text())
    return [g for g in data["groups"] if g["status"] == "include"]


def get_epochs(repos):
    epochs = {}
    for owner, repo, path in repos:
        for ref in refs_for(owner, repo):
            out = subprocess.run(["git", "-C", str(path), "log", ref, "--format=%H %at"],
                                  capture_output=True, text=True).stdout
            for line in out.splitlines():
                parts = line.split(" ")
                if len(parts) == 2:
                    h, t = parts
                    epochs[h] = int(t)
    return sorted(epochs.values())


def cluster(epochs, gap_days=GAP_DAYS):
    gap_seconds = gap_days * 86400
    clusters = [[epochs[0]]]
    for e in epochs[1:]:
        if e - clusters[-1][-1] > gap_seconds:
            clusters.append([e])
        else:
            clusters[-1].append(e)
    return clusters


def fmt_day(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%d")


def main():
    groups = load_groups()
    result = {}
    total_bursts = 0
    for group in groups:
        name = group["name"]
        repos = [(e["owner"], e["repo"], CLONES_DIR / name / e["owner"] / e["repo"]) for e in group["repos"]]
        epochs = get_epochs(repos)
        if not epochs:
            print(f"{name:<22} NO COMMITS FOUND -- skipping")
            continue
        clusters = [c for c in cluster(epochs) if max(1.0, (c[-1] - c[0]) / 86400) > MIN_ACTIVE_DAYS]
        if not clusters:
            print(f"{name:<22} all clusters below MIN_ACTIVE_DAYS -- skipping")
            continue
        bursts = []
        for c in clusters:
            active_days = max(1.0, (c[-1] - c[0]) / 86400)
            bursts.append({
                "start": fmt_day(c[0]),
                "end": fmt_day(c[-1]),
                "commits": len(c),
                "active_days": round(active_days, 1),
                "commits_per_day": round(len(c) / active_days, 3),
            })
        result[name] = bursts
        total_bursts += len(bursts)

        label = name if len(bursts) == 1 else f"{name} ({len(bursts)} bursts)"
        print(f"\n{label}")
        burst_names = [name] if len(bursts) == 1 else [f"{name}{i+1}" for i in range(len(bursts))]
        for bn, b in zip(burst_names, bursts):
            gap_note = ""
            print(f"  {bn:<16} {b['start']} -> {b['end']}  "
                  f"commits={b['commits']:<5} active_days={b['active_days']:<7} "
                  f"commits/day={b['commits_per_day']}")
        # show the idle gap that preceded each burst after the first, so the
        # 120-day threshold's effect is visible, not just its result
        for i in range(1, len(clusters)):
            gap = (clusters[i][0] - clusters[i - 1][-1]) / 86400
            print(f"    [idle gap before burst {i+1}: {gap:.0f} days]")

    out_path = Path(__file__).parent / "bursts.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\n{sum(len(v) for v in result.values())} bursts total across {len(result)} projects "
          f"(gap threshold: {GAP_DAYS} days)")
    print(f"Wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
