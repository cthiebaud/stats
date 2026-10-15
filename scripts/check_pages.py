import json
import subprocess
from pathlib import Path

import yaml

groups = yaml.safe_load((Path(__file__).resolve().parent.parent / "repos.yaml").read_text())["groups"]
pairs = [
    {"group": g["name"], "status": g["status"], "owner": e["owner"], "repo": e["repo"]}
    for g in groups
    for e in g["repos"]
]

results = []
for p in pairs:
    group, status, owner, repo = p["group"], p["status"], p["owner"], p["repo"]
    out = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}/pages"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        continue  # Pages not enabled (404) or no access
    try:
        d = json.loads(out.stdout)
    except json.JSONDecodeError:
        continue
    results.append({
        "group": group, "status": status, "owner": owner, "repo": repo,
        "html_url": d.get("html_url"), "cname": d.get("cname"),
        "pages_status": d.get("status"), "build_type": d.get("build_type"),
    })

for r in results:
    print(f"{r['group']:<20} {r['status']:<8} {r['owner']}/{r['repo']:<35} url={r['html_url']:<45} cname={r['cname']} status={r['pages_status']}")

with open(Path(__file__).resolve().parent / "pages_check.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\n{len(results)} repos have Pages enabled (out of {len(pairs)} checked).")
