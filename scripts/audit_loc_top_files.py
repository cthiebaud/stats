import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, "scripts")
from manual_excludes import MANUAL_EXCLUDES

LOC_EXCLUDE_LANGS = "SVG,JSON,YAML,CSV,XML"


def glob_to_regex(pattern):
    return r"(^|/)" + re.escape(pattern).replace(r"\*", ".*") + "$"


groups = [g for g in yaml.safe_load(Path("repos.yaml").read_text())["groups"] if g["status"] == "include"]

THRESHOLD = 300
for group in groups:
    for entry in group["repos"]:
        owner, repo = entry["owner"], entry["repo"]
        key = f"{owner}/{repo}"
        path = Path("clones") / group["name"] / owner / repo
        cmd = ["cloc", ".", f"--exclude-lang={LOC_EXCLUDE_LANGS}", "--by-file", "--json"]
        pats = MANUAL_EXCLUDES.get(key)
        if pats:
            cmd += ["--fullpath", "--not-match-f=(" + "|".join(glob_to_regex(p) for p in pats) + ")"]
        out = subprocess.run(cmd, capture_output=True, text=True, cwd=path).stdout
        try:
            d = json.loads(out)
        except json.JSONDecodeError:
            continue
        items = sorted(
            [(k, v["code"]) for k, v in d.items() if isinstance(v, dict) and "code" in v and k != "SUM"],
            key=lambda kv: -kv[1],
        )
        top = [(k, v) for k, v in items if v >= THRESHOLD]
        if top:
            print(f"\n=== {group['name']:<18} {key}  (total={d['SUM']['code']}) ===")
            for k, v in top[:8]:
                print(f"  {v:>7}  {k}")
