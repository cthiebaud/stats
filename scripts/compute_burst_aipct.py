#!/usr/bin/env python3
"""Re-measure aiPct per BURST instead of per project -- the known honesty gap
flagged in index.html's own footer (bwv1, 2022, predates Claude Code, was
showing bwv2's 2025 blended 3.4% only because they shared a project average).

Formula (reverse-engineered from the existing project-level values, which
matched this exactly and nothing else -- confirmed against ciaccona's known
0.5%, which only "any finding" reproduces; medium+/high-only both give 0.0%):
  aiPct = 100 * (# commits with disclosure confidence != "none") / (# commits)

`disclosure scan --range=BASE..HEAD` needs a parent commit as BASE, which a
project's very first commit doesn't have, and disclosure rejects the
empty-tree sentinel git itself accepts for this case ("reading base commit:
object not found"). Sidestepped by scanning each repo's FULL history once
(cheap at this scale) and filtering results to each burst's own commits
myself, by epoch -- same technique compute_bursts.py/compute_burst_loc.py
already use, rather than relying on disclosure's own range filtering.

Run with: python3 scripts/compute_burst_aipct.py
(Needs chaoss/disclosure on PATH or at /tmp/disclosure-bin/disclosure --
GOBIN=/tmp/disclosure-bin go install github.com/chaoss/disclosure@latest)
"""
import json
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"
CLONES_DIR = ROOT / "clones"
BURSTS_JSON = Path(__file__).parent / "bursts.json"

DISCLOSURE = shutil.which("disclosure") or "/tmp/disclosure-bin/disclosure"


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


def commit_epochs(path):
    out = subprocess.run(["git", "-C", str(path), "log", "--format=%H %at"],
                          capture_output=True, text=True).stdout
    epochs = {}
    for line in out.splitlines():
        h, t = line.split(" ")
        epochs[h] = int(t)
    return epochs


def disclosure_confidence(path):
    out = subprocess.run([DISCLOSURE, "scan", "--format=json", str(path)],
                          capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return {}
    return {c["hash"]: c["confidence"] for c in d.get("commits", [])}


def main():
    groups = load_groups()
    bursts_by_project = json.loads(BURSTS_JSON.read_text())

    result = {}
    for project, bursts in bursts_by_project.items():
        group = groups[project]
        paths = [CLONES_DIR / project / e["owner"] / e["repo"] for e in group["repos"]]

        # one full-history scan per repo, shared across all of this project's bursts
        epochs_by_path = {p: commit_epochs(p) for p in paths}
        confidence_by_path = {p: disclosure_confidence(p) for p in paths}

        names = [project] if len(bursts) == 1 else [f"{project}{i+1}" for i in range(len(bursts))]
        for burst_name, burst in zip(names, bursts):
            lo, hi = day_bounds_epoch(burst["start"], burst["end"])
            total = 0
            flagged = 0
            for p in paths:
                epochs = epochs_by_path[p]
                conf = confidence_by_path[p]
                for h, t in epochs.items():
                    if lo <= t <= hi:
                        total += 1
                        if conf.get(h, "none") != "none":
                            flagged += 1
            pct = round(100 * flagged / total, 1) if total else None
            result[burst_name] = pct
            print(f"  {burst_name:<20} commits_in_range={total:<5} flagged={flagged:<5} aiPct={pct}")

    out_path = Path(__file__).parent / "burst_aipct.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
