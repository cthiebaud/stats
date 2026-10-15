import subprocess

checks = [
    ("clones/parimagine/parimagine/parimagine", "src/main/webapp/jquery.js", "parimagine jquery.js"),
    ("clones/parimagine/parimagine/parimagine", "src/test/resources/photos*.sql", "parimagine photos*.sql"),
    ("clones/covid/usa-covid-aequologica-net/usa.covid.aequologica.net", "*wavetable.js", "covid(usa) wavetable.js"),
    ("clones/covid/covid-aequologica-net/covid-aequologica-net.github.io", "*wavetable.js", "covid(gh.io) wavetable.js"),
    ("clones/sangiovannilipioni/sangiovannilipioni/sangiovannilipioni.github.io", "schema.docs.graphql", "sangio schema.docs.graphql"),
    ("clones/bookshelves/cthiebaud/bookshelves", "isbn-ja2.txt", "bookshelves isbn-ja2.txt"),
    ("clones/bookshelves/cthiebaud/bookshelves", "isbn.txt", "bookshelves isbn.txt"),
    ("clones/bookshelves/cthiebaud/bookshelves", "qwe.txt", "bookshelves qwe.txt"),
    ("clones/aletheia/cthiebaud/truth-reservoir", "*greeks.txt", "truth-reservoir greeks.txt"),
]

for path, pattern, label in checks:
    print(f"=== {label} ===")
    out = subprocess.run(
        ["git", "-C", path, "log", "--all", "--full-history", "--diff-filter=D",
         "--name-only", "--format=", "--", pattern],
        capture_output=True, text=True,
    ).stdout
    lines = sorted(set(out.splitlines()))
    for l in lines[:6]:
        print(" ", l)
    if not lines:
        print("  (no deletion found matching this pattern)")
