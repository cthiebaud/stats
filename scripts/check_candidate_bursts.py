#!/usr/bin/env python3
"""Ad hoc: check whether previously-excluded groups contain a burst that
would look legitimate under the current burst-chart model, now that the
unit is "episode of real activity" rather than "whole project." Reuses
compute_bursts.py's exact clustering rule (120-day gap, drop single-
calendar-day clusters) against clones/_candidates/<owner>/<repo>.

Run with: python3 scripts/check_candidate_bursts.py
"""
import datetime
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "clones" / "_candidates"

GAP_DAYS = 120
MIN_ACTIVE_DAYS = 1.0

CANDIDATES = {
    "iroif": [("cthiebaud", "iroif")],
    "aequologica": [("aequologica", "aequologica.github.io"), ("aequologica", "deputes-scraper")],
    "cthiebaud.github.io": [("cthiebaud", "cthiebaud.github.io")],
    "openricard": [("cthiebaud", "openricard.net")],
    "klam": [("cthiebaud", "klam")],
    "emugnier": [("cthiebaud", "emugnier")],
    "openmozart": [("cthiebaud", "openmozart.net")],
    "athenaeum (5 repos listed)": [
        ("athenaeum-brew", "password-validator-acceptance"),
        ("athenaeum-brew", "password-validator"),
        ("athenaeum-brew", "password-validator-impl"),
        ("athenaeum-brew", "questioneer"),
        ("cthiebaud", "mythos"),
    ],
}


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


for name, repos in CANDIDATES.items():
    paths = [CAND / o / r for o, r in repos]
    epochs = get_epochs(paths)
    print(f"\n=== {name} ===")
    if not epochs:
        print("  NO COMMITS FOUND")
        continue
    print(f"  total commits (all time, all forks of repo in group): {len(epochs)}")
    clusters_all = cluster(epochs)
    kept = [c for c in clusters_all if max(1.0, (c[-1] - c[0]) / 86400) > MIN_ACTIVE_DAYS]
    dropped = len(clusters_all) - len(kept)
    if not kept:
        print(f"  all {len(clusters_all)} cluster(s) are single-calendar-day blips -- nothing burst-worthy")
        continue
    for c in kept:
        active_days = max(1.0, (c[-1] - c[0]) / 86400)
        print(f"  BURST  {fmt_day(c[0])} -> {fmt_day(c[-1])}  "
              f"commits={len(c):<5} active_days={active_days:<7.1f} "
              f"commits/day={len(c)/active_days:.2f}")
    if dropped:
        print(f"  ({dropped} single-day blip cluster(s) dropped, same as the main chart's rule)")
