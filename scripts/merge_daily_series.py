#!/usr/bin/env python3
"""Merge scripts/lines_changed_by_day.json's per-repo series into one
per-project {date: lines_changed} series each, summed across a group's repos,
then winsorize each project's series at its own 90th percentile.

Winsorizing (capping outliers to a percentile value, rather than zeroing or
dropping them) handles single-day magnitudes no human plausibly hand-types in
a day (e.g. an 11,532-line day traced to a bulk "initial import" commit,
confirmed 2026-10-15) -- without pretending to forensically clear every such
spike by file-path, and without losing the signal that *something* big
happened that day (it still renders as the tallest bar, just capped).
Deliberately NOT applied to loc/commits/active_days -- only to this series,
which exists purely to show per-day rhythm for the sparkline.

Run with: python3 scripts/merge_daily_series.py
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WINSORIZE_PERCENTILE = 90


def percentile(sorted_values, pct):
    if not sorted_values:
        return 0
    k = (len(sorted_values) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def main():
    data = json.loads((ROOT / "scripts" / "lines_changed_by_day.json").read_text())
    merged = {}
    for group, repos in data.items():
        daily = defaultdict(int)
        for series in repos.values():
            for date, n in series.items():
                daily[date] += n
        sorted_vals = sorted(daily.values())
        cap = percentile(sorted_vals, WINSORIZE_PERCENTILE)
        capped = {date: round(min(n, cap), 1) for date, n in daily.items()}
        merged[group] = dict(sorted(capped.items()))

    out_path = ROOT / "scripts" / "project_daily_series.json"
    out_path.write_text(json.dumps(merged, indent=2))
    for group, series in merged.items():
        print(f"  {group:<20} days={len(series):<5} total={sum(series.values())}")
    print(f"\nWrote {out_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
