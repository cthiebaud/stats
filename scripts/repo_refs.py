"""Which git refs to scan for a given repo -- HEAD plus any curated
`extra_refs` from repos.yaml.

Added 2026-10-15: every pipeline script previously only ever read `git log`
on the checked-out default branch, silently missing any work that happened
on a branch that was never merged. Confirmed this really loses real work
(not just edge cases): usa.covid.aequologica.net's `backup` branch has 148
commits, June-December 2020, with NO common ancestor with `master` (a
from-scratch restart, not just an unmerged branch) -- Christophe's own
memory of when covid development started was right; "master" alone
understated it by about 6 months. vinyl's `no_color_no_font` branch has 58
more genuine commits spanning almost 3 years.

Deliberately NOT auto-scanning `git branch -a`/`--all` for every repo: an
audit (scripts/audit_hidden_branches.py) found every repo's branch list
cluttered with dependabot/* (bot-authored dependency bumps, 1 commit each,
never merged -- zero signal) and gh-pages (confirmed, twice, to be deploy-
script build output -- hashed bundle filename renames, manifest.json,
.output/ artifacts -- not hand-written code even though git credits
Christophe as the author, since he's the one who ran the deploy script).
Auto-including either category would inject pure noise. `extra_refs` is a
curated allowlist instead, same philosophy as manual_excludes.py's vendor-
file denylist: verified real, human-authored, non-build-output work only.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPOS_YAML = ROOT / "repos.yaml"


def _load():
    data = yaml.safe_load(REPOS_YAML.read_text())
    refs = {}
    for g in data["groups"]:
        if g["status"] != "include":
            continue
        for e in g.get("repos", []):
            key = f"{e['owner']}/{e['repo']}"
            refs[key] = ["HEAD"] + list(e.get("extra_refs", []))
    return refs


_REFS_BY_REPO = _load()


def refs_for(owner, repo):
    """List of git refs to scan for this repo: always includes HEAD,
    plus any curated extra_refs from repos.yaml."""
    return _REFS_BY_REPO.get(f"{owner}/{repo}", ["HEAD"])
