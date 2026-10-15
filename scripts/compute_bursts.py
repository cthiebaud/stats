#!/usr/bin/env python3
"""Split each project's commit history into bursts: gap-clustered episodes of
genuine activity, same clustering rule as gather_data.py's active_days() (120-
day gap threshold) but keeping each cluster as its own row instead of summing
their spans into one project-level total.

Uses real commit epochs (git log, not the cloc-filtered dailySeries), since a
day with only non-code changes should still count as "the burst is alive" --
narrower than what the sparkline trail shows.

Two clustering passes, added 2026-10-15 after covid's real history exposed a
gap in the single-pass 120-day rule: a pairwise-gap clusterer only ever checks
ADJACENT commits, so a handful of isolated "bridge" commits -- each individually
less than 120 days from its neighbor, but together spanning 11 months of mostly
dead air -- chained covid's real June 2020 start, December 2020 push, and May
2021 wrap-up into one misleadingly continuous burst. Fixed with a second,
finer pass (45 days) INSIDE each coarse cluster: distinct calendar days are
re-clustered at the finer threshold, trivial (<2-day) fragments are reabsorbed
into their nearest substantial neighbor instead of being allowed to bridge two
real episodes, and the result is split back into per-epoch sub-clusters.
Verified against every other multi-burst project (ciaccona, bwv, music,
sangiovannilipioni, openmozart) at fine thresholds of 30/45/60 days: zero
regressions, identical output across all three -- only covid changes, 1 -> 3
bursts (confirmed against Christophe's own memory of two separate pre-2021
episodes, which this refines to three once the isolated October bridge commit
and the near-miss January->May gap are no longer allowed to merge genuinely
separate episodes).

`active_days` changed meaning the same day: it used to be the burst's
calendar SPAN (last commit epoch - first commit epoch), which silently
counted idle gaps *inside* a burst as if they were working time -- diluting
the rate for any sparse burst (confirmed on gear: 18.6 span-days but only 11
distinct days with a commit, a 59%-dense burst). `active_days` is now the
COUNT of distinct calendar days with >=1 commit; every downstream per-day
rate (commits/day, and compute_burst_netloc.py's net-lines/day) divides by
this corrected denominator, not the span. This changes the *existing*
chart's commits/day values too, not just new metrics -- it was always wrong
for sparse bursts, not just newly relevant.

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
FINE_GAP_DAYS = 45
MIN_DAYS_IN_SUBCLUSTER = 2


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


def fmt_day(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%d")


def cluster(epochs, gap_days=GAP_DAYS):
    gap_seconds = gap_days * 86400
    clusters = [[epochs[0]]]
    for e in epochs[1:]:
        if e - clusters[-1][-1] > gap_seconds:
            clusters.append([e])
        else:
            clusters[-1].append(e)
    return clusters


def split_cluster(epochs, fine_gap_days=FINE_GAP_DAYS, min_days=MIN_DAYS_IN_SUBCLUSTER):
    """Re-split one coarse (120-day) cluster at a finer day-level granularity,
    reabsorbing trivial fragments into their nearest substantial neighbor
    instead of letting them bridge two real episodes. See module docstring."""
    by_day = {}
    for e in epochs:
        by_day.setdefault(fmt_day(e), []).append(e)
    day_dts = sorted(datetime.datetime.strptime(d, "%Y-%m-%d") for d in by_day)

    fine = [[day_dts[0]]]
    for d in day_dts[1:]:
        if (d - fine[-1][-1]).days > fine_gap_days:
            fine.append([d])
        else:
            fine[-1].append(d)

    substantial_idx = [i for i, f in enumerate(fine) if len(f) >= min_days]
    if not substantial_idx:
        return [epochs]  # whole coarse cluster is trivial; leave as-is (MIN_ACTIVE_DAYS drops it upstream)

    merged_days = [list(fine[i]) for i in substantial_idx]
    for i, f in enumerate(fine):
        if i in substantial_idx:
            continue
        nearest = min(substantial_idx,
                       key=lambda si: min(abs((f[0] - fine[si][0]).days), abs((f[-1] - fine[si][-1]).days)))
        merged_days[substantial_idx.index(nearest)].extend(f)

    result = []
    for group in merged_days:
        day_strs = {d.strftime("%Y-%m-%d") for d in group}
        sub_epochs = sorted(e for d in day_strs for e in by_day[d])
        result.append(sub_epochs)
    result.sort(key=lambda c: c[0])
    return result


def active_day_count(epochs):
    return len({fmt_day(e) for e in epochs})


def main():
    groups = load_groups()
    result = {}
    for group in groups:
        name = group["name"]
        repos = [(e["owner"], e["repo"], CLONES_DIR / name / e["owner"] / e["repo"]) for e in group["repos"]]
        epochs = get_epochs(repos)
        if not epochs:
            print(f"{name:<22} NO COMMITS FOUND -- skipping")
            continue

        coarse = cluster(epochs)
        clusters = []
        for c in coarse:
            clusters.extend(split_cluster(c))
        clusters = [c for c in clusters if active_day_count(c) > 1]
        if not clusters:
            print(f"{name:<22} all clusters below MIN_ACTIVE_DAYS -- skipping")
            continue

        bursts = []
        for c in clusters:
            active_days = active_day_count(c)
            bursts.append({
                "start": fmt_day(c[0]),
                "end": fmt_day(c[-1]),
                "commits": len(c),
                "active_days": active_days,
                "commits_per_day": round(len(c) / active_days, 3),
            })
        result[name] = bursts

        label = name if len(bursts) == 1 else f"{name} ({len(bursts)} bursts)"
        print(f"\n{label}")
        burst_names = [name] if len(bursts) == 1 else [f"{name}{i+1}" for i in range(len(bursts))]
        for bn, b in zip(burst_names, bursts):
            print(f"  {bn:<16} {b['start']} -> {b['end']}  "
                  f"commits={b['commits']:<5} active_days={b['active_days']:<4} "
                  f"commits/day={b['commits_per_day']}")
        for i in range(1, len(clusters)):
            gap = (clusters[i][0] - clusters[i - 1][-1]) / 86400
            print(f"    [idle gap before burst {i+1}: {gap:.0f} days]")

    out_path = Path(__file__).parent / "bursts.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\n{sum(len(v) for v in result.values())} bursts total across {len(result)} projects "
          f"(coarse gap: {GAP_DAYS}d, fine gap: {FINE_GAP_DAYS}d)")
    print(f"Wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
