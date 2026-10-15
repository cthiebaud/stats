#!/usr/bin/env python3
"""For each burst found by compute_bursts.py, compute the LOC snapshot "as of
the end of this burst" -- the circle-size measure for the burst chart.

For a burst ending at date D: for every repo in the project's group, find
that repo's own latest commit at or before D (a repo with no commits yet by D
contributes nothing -- it didn't exist in the project at that point), check
it out (detached), run the same cloc filter gather_data.py's loc_for() uses
(language exclude list + manual vendor/data-dump excludes), sum across repos,
then restore the repo to its original ref so later scripts still find HEAD
checked out as expected.

Run with: python3 scripts/compute_burst_loc.py
(Takes a while -- one checkout+cloc per repo per burst.)
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"
CLONES_DIR = ROOT / "clones"
BURSTS_JSON = Path(__file__).parent / "bursts.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manual_excludes import MANUAL_EXCLUDES  # noqa: E402
from repo_refs import refs_for  # noqa: E402

LOC_EXCLUDE_LANGS = "SVG,JSON,YAML,CSV,XML"


def glob_to_regex(pattern):
    return r"(^|/)" + re.escape(pattern).replace(r"\*", ".*") + "$"


def load_groups():
    data = yaml.safe_load(REPOS_YAML.read_text())
    return {g["name"]: g for g in data["groups"] if g["status"] == "include"}


def day_end_epoch(date_str):
    y, m, d = (int(x) for x in date_str.split("-"))
    dt = datetime.datetime(y, m, d, 23, 59, 59, tzinfo=datetime.timezone.utc)
    return int(dt.timestamp())


def commit_list(owner, repo, path):
    """[(epoch, sha), ...] sorted ascending, across HEAD + any curated
    extra_refs, deduped by sha."""
    commits = {}
    for ref in refs_for(owner, repo):
        out = subprocess.run(["git", "-C", str(path), "log", ref, "--format=%at %H"],
                              capture_output=True, text=True).stdout
        for line in out.splitlines():
            epoch, sha = line.split(" ")
            commits[sha] = int(epoch)
    return sorted((epoch, sha) for sha, epoch in commits.items())


def latest_at_or_before(commits, cutoff_epoch):
    latest = None
    for epoch, sha in commits:
        if epoch <= cutoff_epoch:
            latest = sha
        else:
            break
    return latest


def current_ref(path):
    return subprocess.run(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True).stdout.strip()


def cloc_at(path, owner_repo):
    cmd = ["cloc", ".", f"--exclude-lang={LOC_EXCLUDE_LANGS}", "--json"]
    patterns = MANUAL_EXCLUDES.get(owner_repo)
    if patterns:
        cmd += ["--fullpath", "--not-match-f=" + "(" + "|".join(glob_to_regex(p) for p in patterns) + ")"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=path).stdout
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return 0
    return d.get("SUM", {}).get("code", 0)


def main():
    groups = load_groups()
    bursts_by_project = json.loads(BURSTS_JSON.read_text())

    result = {}
    for project, bursts in bursts_by_project.items():
        group = groups[project]
        repo_entries = [(e["owner"], e["repo"]) for e in group["repos"]]
        paths = {f"{o}/{r}": CLONES_DIR / project / o / r for o, r in repo_entries}
        commits_cache = {f"{o}/{r}": commit_list(o, r, CLONES_DIR / project / o / r) for o, r in repo_entries}
        original_refs = {key: current_ref(path) for key, path in paths.items()}

        # A repo that stops receiving commits partway through a multi-burst
        # project (e.g. cthiebaud/ciaccona, frozen since 2023-05-24 once
        # musicollator/ciaccona took over) was being re-counted in FULL
        # toward every later burst's LOC -- the same static snapshot added
        # again and again, since "latest commit at or before cutoff"
        # resolves to the same frozen SHA every time. Fixed by only
        # re-running checkout+cloc when a repo's resolved SHA has actually
        # changed since the last burst it contributed to (bursts are
        # processed in chronological order, same order compute_bursts.py
        # emitted them) -- a frozen repo's LOC counts once, in the first
        # burst after it stops moving, not forever after.
        last_counted_sha = {}
        names = [project] if len(bursts) == 1 else [f"{project}{i+1}" for i in range(len(bursts))]
        for burst_name, burst in zip(names, bursts):
            cutoff = day_end_epoch(burst["end"])
            total_loc = 0
            contributing = []
            for key, path in paths.items():
                sha = latest_at_or_before(commits_cache[key], cutoff)
                if sha is None:
                    continue  # repo didn't exist yet as of this burst's end
                if sha == last_counted_sha.get(key):
                    contributing.append(f"{key}@{sha[:7]}=(unchanged, not re-counted)")
                    continue
                last_counted_sha[key] = sha
                subprocess.run(["git", "-C", str(path), "checkout", "--quiet", "--detach", sha],
                                capture_output=True)
                loc = cloc_at(path, key)
                total_loc += loc
                contributing.append(f"{key}@{sha[:7]}={loc}")
                subprocess.run(["git", "-C", str(path), "checkout", "--quiet", original_refs[key]],
                                capture_output=True)
            result[burst_name] = total_loc
            print(f"  {burst_name:<20} end={burst['end']}  loc={total_loc:<8} ({', '.join(contributing)})")

    out_path = Path(__file__).parent / "burst_loc.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
