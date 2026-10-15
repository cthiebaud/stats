# ai-dev-efficiency — handoff / continuation prompt

Paste this whole file as your first message in a new session opened on this
folder, or just tell Claude to read it.

## What this project is

Christophe wants a rigorous, honest chart for a LinkedIn post, testing his own
intuition: *"the more I develop with [Claude Code], the more efficient I am —
culminating with mundial and gear, where I no longer write any code myself."*

The chart lives in [index.html](index.html) — open it directly in a browser.
It was built and iterated as a Claude Artifact at
`https://claude.ai/code/artifact/c9e94bf8-3385-4752-8cd2-3584ed174aea` (title
"AI Development Efficiency", favicon 📈) — if continuing in claude.ai rather
than locally, read/update that URL instead of the local file.

## The metric, and why it's shaped this way

For each of 11 personal **hobby** projects (professional work, course
assignments, joke projects, and tiny ones are explicitly excluded — see
"Projects in scope" below), the chart plots:

- **X position & span** = real calendar start→end dates (not index order —
  spans are allowed to overlap).
- **Y position** = `scope / active_days` — "scope" is Christophe's own
  subjective 1–5 rating of how much feature scope the project represents
  (there is no honest automatable proxy for "features" across such different
  projects — LOC was considered and rejected as the y-axis for exactly this
  reason, see "Rejected approaches" below). "Active days" is NOT raw
  calendar lifespan — see next point.
- **Line thickness** = total commit count (sqrt-scaled, so it's
  area-proportional, not length-proportional).
- **Color** = one hue per project (see "Color assignment" below); lightness
  darkens with % of commits attributed to AI tooling (see "AI attribution").

### Active-days methodology (important, non-obvious)

"Lifespan" is not `last_commit − first_commit`. Real hobby projects have long
idle gaps (months, sometimes years) that shouldn't count as "active
development." The method: cluster commit timestamps by gap (120-day
threshold), then **sum each cluster's own day-span** — not just the largest
cluster, not the full outer range. This is immune to the arbitrary choice of
gap length (120 days vs. 90 vs. 180 barely changes the result) because it's
summing genuine work episodes rather than picking one.

Implemented in [scripts/gather_data.py](scripts/gather_data.py) as
`active_days()`.

### LOC methodology

`cloc --git <ref> --exclude-lang=SVG,JSON,YAML,CSV --json`, **plus** manual
exclusion of vendored libraries and auto-generated data-as-code files
discovered by inspecting cloc's per-file breakdown (never trust the raw
total — repeatedly found confounds: vendored jQuery/Bootstrap/Handlebars,
vendored Prism.js, vendored SVG icon sets, large JSON/word-list data files,
auto-generated timing-data `.js` files). The repo list in
`ENTRIES` inside `gather_data.py` already reflects these exclusions (by
pointing at the right refs/repos) — LOC itself ended up **not used on either
axis** of the final chart (only commits and active-days are), but it's still
computed and shown in the tooltip/table for context.

### AI-attribution methodology

Measured with **[chaoss/disclosure](https://github.com/chaoss/disclosure)**
(a real external tool, not a homegrown heuristic — Christophe was explicit
about this: *"I'd rather use a half-finish external tool than build our own
tooling. In the vendor vs. homegrown battle, I've since decades chosen my
camp."*). It detects committer emails, co-author trailers, branch-naming
conventions, and tool-mentions for Claude Code, Cursor, Copilot, ChatGPT, and
Aider. A naive grep for "claude"/"anthropic" in commit messages was tried
first and **missed real signal entirely** (0% where disclosure found real
traces) — don't regress to that approach.

Caveat baked into the chart's footer: disclosure only catches *disclosed,
git-level* traces, so chat-based AI use with no trailer or tool mention left
in the repo (manually typed/pasted) is invisible to it — true involvement may
be higher than shown, especially before mid-2025.

`aiPct` and `scope` are **not** computed by `gather_data.py` — they come from
disclosure runs (ad hoc, per repo/org) and from Christophe's own subjective
rating respectively. They're hand-entered into `index.html`'s `data` array.

### Color assignment (fixed a real bug already — don't reintroduce it)

Hue is assigned by **golden-angle stepping** (`i * 137.50776° mod 360`)
through projects sorted by start date. An earlier greedy "maximize distance
from the one time-overlapping neighbor" approach was tried and **collapsed to
just two alternating hues** (verified: ciaccona/sangiosleague/covid/parimagine
all landed on hue 0°, sangiovannilipioni/bwv/earthlydelights all on 180°) —
because most items only conflict with one immediate predecessor, so "pick the
exact opposite" oscillates binary instead of spreading. Golden-angle stepping
has no small-integer resonances, so time-adjacent indices land far apart in
hue and stay that way — same principle as phyllotaxis/sunflower seed
placement. Verified worst-case hue separation among any time-close pair:
52.5°, vs. 0° before.

Lightness: `L = 68 - 36 * sqrt(aiPct/100)` (sqrt so even a few % of
AI-attribution shows a visible step, rather than needing to approach 100%).

## Projects in scope, and why others aren't

Final 11: **parimagine, earthlydelights, covid, sangiosleague,
sangiovannilipioni, ciaccona, bookshelves, aletheia, bwv, mundial, gear.**

Explicitly excluded, per Christophe's direct instructions — don't
re-add without asking:
- **iroif, aequologica, cthiebaud.com** — not true "projects" (infrastructure/meta)
- **openricard** — a joke project
- **klam, emugnier** — too tiny
- **music, openmozart** — too tiny
- **hat** — a professional assignment, not hobby work
- **athenaeum** — a side project done *on* a professional course, not hobby

`parimagine` and `earthlydelights` were almost missed entirely — Christophe
noticed their absence himself ("I wonder why these are absent, both are old
truly hobby projects") and they were folded in afterward. If auditing for
completeness again, check both the user's own repos **and their GitHub orgs**
— a prior "why was 2022 empty?" investigation found real missing activity
hiding in orgs, not just personal repos.

Old pre-migration repos were folded into their modern successor's numbers
(not kept as separate chart entries): `cthiebaud/ciaccona` → `ciaccona`,
`cthiebaud/bwv543` → `bwv`. `musicollator/ciaccona-stationary` contributes
commits/days but ~0 LOC (confirmed by Christophe: "no code at all," a
corrupted git pack there blocks `cloc`/disclosure but not `git log`).

## Rejected approaches (don't redo these — they were tried and abandoned)

- **LOC as the "effort" axis** — Christophe's own objection: *"LOC is a
  measure of effort, but a much better one would be 'features.' One can be so
  efficient to output more feature with less lines."* No satisfactory
  automated feature-count proxy was found, so his own 1–5 scope rating is
  used instead, honestly labeled as subjective in the chart's footer.
- **Grep for AI keywords in commit messages** — see AI-attribution section above.
- **Homegrown AI-content-detection heuristics** (em-dash frequency, buzzword
  patterns in diffs) — explored, then explicitly rejected by Christophe in
  favor of using the real `disclosure` tool.
- **Greedy conflict-based hue assignment** — see Color assignment above.
- **A single fixed gap-threshold "largest cluster" lifespan** — rejected in
  favor of the gap-clustered sum, for robustness to the threshold choice.

## Open / unfinished work

1. **Mini-bar-chart-per-project (sparkline) redesign** — the last unresolved
   feature request. Christophe asked to replace each project's current flat
   horizontal line with a small embedded bar chart showing **lines changed
   per time bucket**, positioned along that project's real time span — so
   the row shows *rhythm* of work (bursts vs. steady trickle), not just a
   single flat value. Proposed synthesis (not yet confirmed with Christophe):
   keep the row's vertical anchor = `scope/active_days` (preserving
   cross-project comparability), but draw the row as a sparkline instead of
   a flat line, with bars extending from that anchor.
   - **Bucket size is explicitly unresolved** — Christophe asked "a day, a
     week, a month?" and left it for us to decide. Durations range from 19
     active-days (gear) to 1039 (earthlydelights), so a single fixed bucket
     size won't work for all projects (weekly buckets = ~3 bars for gear but
     ~150 for earthlydelights). Proposed approach: adaptive bucket size per
     project, targeting roughly 15–25 bars per sparkline, snapped to the
     nearest of {1 day, 1 week, 1 month} for interpretability.
   - The raw per-commit `(epoch, lines_changed)` series needed for this is
     already gathered, in `scripts/lines_changed_series.json` — re-run
     `scripts/gather_data.py` to refresh it if repos have moved on.
2. **"vert axis is 'efficiency of dev'"** — Christophe's own phrasing for the
   y-axis in his last round of feedback before this project was split out.
   Currently labeled "Scope delivered per day" in the chart. Unclear whether
   he wants the label literally renamed to something like "Efficiency of
   dev" or whether he was just describing/confirming what the axis already
   means. Worth a quick clarifying question rather than guessing.

## Repo / environment notes

- All source repos live under `~/github.com/<org>/<repo>` on this machine.
- `chaoss/disclosure` (Go) was installed via
  `GOBIN=/tmp/disclosure-bin go install github.com/chaoss/disclosure@latest`
  — required `brew install go` first since the system Go at `/usr/local/go`
  was an old 1.20.3 (user confirmed it was safe to upgrade the system Go).
- This folder has **no git repo yet** ("no git for the moment, but
  probably" — Christophe's words). Ask before running `git init` /
  committing, or just do it if he asks directly in a later session.
- Shell quirk (seen repeatedly in the parent `cthiebaud.github.io` session,
  may recur here): complex multi-line bash loops/heredocs sometimes fail with
  `command not found` for basic utilities despite a correct PATH. Workaround
  that always worked: write the logic as a standalone `.py` file and run
  `python3 script.py` instead of inline complex bash.

## Related, separate work (not part of this project)

`cthiebaud.github.io`'s `index.html` has its own, simpler "domains" table
(Peak Activity / Last Commit / Commits / LOC columns) with its own
maintenance script `scripts/update_domain_stats.py` in that repo — it covers
*all* 19 of Christophe's public domains (including the ones excluded here)
and is unrelated to the LinkedIn-post chart's scope/AI-attribution analysis,
beyond sharing some methodology (the active-days clustering approach
originated there). Don't conflate the two.
