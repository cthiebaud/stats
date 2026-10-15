#!/usr/bin/env python3
"""Regenerate index.html's `data` array and `dailySeries` object in place
from the pipeline's JSON outputs (bursts.json, burst_loc.json,
burst_netloc.json, burst_aipct.json, project_daily_series.json) and
repos.yaml's `site` field.

Written 2026-10-15 after assembling these literals by hand twice in one
session (error-prone, ad hoc scratchpad scripts each time) -- see PROMPT.md
"Open / unfinished work". Run this as the LAST step of a full pipeline
re-run, after every scripts/compute_*.py / merge_daily_series.py has been
re-run against updated burst boundaries or repos.yaml changes.

Row order: start date, ascending (matches index.html's existing convention).
`chart: false` is set per-PROJECT (not per burst name) for any project in
CHART_EXCLUDED_PROJECTS, since burst names/counts can change between runs
(e.g. the two-pass clustering fix split earthlydelights 2 -> 5 bursts) --
hardcoding burst names here would silently stop covering new bursts of an
already-excluded project.

Run with: python3 scripts/generate_index_data.py
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
INDEX_HTML = ROOT / "index.html"

# Excluded from the CHART ONLY (not Table view, not repos.yaml) -- real
# bursts, but kept out of the SVG chart for readability. See PROMPT.md's
# "Open / unfinished work" entry on this for the full rationale.
CHART_EXCLUDED_PROJECTS = {"parimagine", "earthlydelights"}


def load_rows():
    bursts = json.loads((SCRIPTS / "bursts.json").read_text())
    burst_loc = json.loads((SCRIPTS / "burst_loc.json").read_text())
    burst_aipct = json.loads((SCRIPTS / "burst_aipct.json").read_text())
    burst_netloc = json.loads((SCRIPTS / "burst_netloc.json").read_text())

    repos = yaml.safe_load((ROOT / "repos.yaml").read_text())
    site_by_project = {g["name"]: g.get("site") for g in repos["groups"] if g["status"] == "include"}

    rows = []
    for project, blist in bursts.items():
        names = [project] if len(blist) == 1 else [f"{project}{i+1}" for i in range(len(blist))]
        for name, b in zip(names, blist):
            rows.append({
                "name": name,
                "project": project,
                "start": b["start"],
                "end": b["end"],
                "commits": b["commits"],
                "activeDays": b["active_days"],
                "loc": burst_loc[name],
                "netLoc": burst_netloc[name],
                "aiPct": burst_aipct[name],
                "site": site_by_project.get(project),
                "chart": project not in CHART_EXCLUDED_PROJECTS,
            })
    rows.sort(key=lambda r: r["start"])
    return rows


def js_val(v):
    return "null" if v is None else json.dumps(v)


def build_data_block(rows):
    lines = ["  const data = ["]
    for r in rows:
        parts = [f'name: {js_val(r["name"])}', f'project: {js_val(r["project"])}',
                  f'start: {js_val(r["start"])}', f'end: {js_val(r["end"])}',
                  f'commits: {r["commits"]}', f'activeDays: {r["activeDays"]}',
                  f'loc: {r["loc"]}', f'netLoc: {r["netLoc"]}', f'aiPct: {r["aiPct"]}',
                  f'site: {js_val(r["site"])}']
        if not r["chart"]:
            parts.append("chart: false")
        lines.append("    { " + ", ".join(parts) + " },")
    lines.append("  ];")
    return "\n".join(lines)


def build_daily_series_line():
    project_daily = json.loads((SCRIPTS / "project_daily_series.json").read_text())
    return "  const dailySeries = " + json.dumps(project_daily, separators=(",", ":")) + ";"


def splice_into_index_html(data_block, daily_series_line):
    lines = INDEX_HTML.read_text().split("\n")

    start = next(i for i, l in enumerate(lines) if l.strip() == "const data = [")
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "];")
    lines[start:end + 1] = data_block.split("\n")

    ds_idx = next(i for i, l in enumerate(lines) if l.startswith("  const dailySeries = {"))
    lines[ds_idx] = daily_series_line

    INDEX_HTML.write_text("\n".join(lines))
    return start, end, ds_idx


def main():
    rows = load_rows()
    data_block = build_data_block(rows)
    daily_series_line = build_daily_series_line()
    start, end, ds_idx = splice_into_index_html(data_block, daily_series_line)
    print(f"Wrote {len(rows)} rows to index.html's data array (lines {start}-{end})")
    print(f"Wrote dailySeries (line {ds_idx})")


if __name__ == "__main__":
    main()
