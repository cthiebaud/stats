# ai-dev-efficiency — handoff / continuation prompt

Paste this whole file as your first message in a new session opened on this
folder, or just tell Claude to read it.

## What this project is

Christophe wants a rigorous, honest chart for a LinkedIn post, testing his own
intuition: *"the more I develop with [Claude Code], the more efficient I am —
culminating with mundial and gear, where I no longer write any code myself."*

The chart lives in [index.html](index.html) — open it directly in a browser,
or visit the deployed copy at **https://stats.cthiebaud.com** (see
"Deployment" below). It started life as a Claude Artifact and was migrated to
a standalone git repo + GitHub Pages site on 2026-10-15 — if an artifact URL
from an earlier session still turns up in old notes, it's superseded; this
repo is now the canonical source.

**This is a git repo** (`github.com/cthiebaud/stats`, pushed), not a loose
folder — commit history itself is part of the record of how this chart's
methodology evolved. `clones/` (the ~8GB of cloned source repos the data
pipeline reads from) is gitignored; everything else is tracked.

## The metric, and why it's shaped this way (rewritten 2026-10-15 — see below)

**The chart's unit changed from "one row per project" to "one row per coding
burst."** This was a deliberate, significant redesign, not a tweak — see
"The burst redesign" below for the full rationale. The original "11/12
projects, one row each, y-axis = scope/day" design is described afterward,
in **Superseded design (kept for history)**, since the reasoning behind
things like the gap-clustering rule and color assignment still applies and
isn't worth re-deriving.

### The burst redesign (current design)

Christophe's framing: a project isn't one continuous effort, it's bursts of
real activity separated by idle gaps, and a burst on the same repo *years*
apart from another burst on that repo is, in every way that matters here, a
*different project* — not one continuous effort that happened to pause. The
single-row-per-project chart was averaging across that gap and hiding
exactly the story the chart exists to tell. The clearest example: `bwv`'s
2022 scaffold (23 commits, 22 LOC) and its 2025 rewrite (662 commits, 13,026
LOC) sit three years apart in the same repo. One blended "bwv" row showed
neither story; two rows (`bwv1`, `bwv2`) show both.

**Burst detection**: same 120-day gap-clustering rule `gather_data.py`'s
`active_days()` already used (see below) — but instead of summing each
cluster's span into one project-level total, **each cluster is now kept as
its own chart row**. Implemented in `scripts/compute_bursts.py`. A cluster
spanning exactly one calendar day (1–3 commits — a lone fix, not a coding
campaign) is **dropped entirely**, not merged into a neighbor. This was
checked against the real distribution, not an arbitrary cutoff: every
current single-day cluster has 1–3 commits, and the smallest *kept*
multi-day burst is 27.2 active days — a real gap, not a tuned threshold.
Result: 14 projects → **22 bursts**.

**Y-axis changed from scope/day to commits/day (per burst).** The old
"scope" field (Christophe's subjective 1–5 whole-project feature-scope
rating) has **no sane per-burst equivalent** — re-rating scope separately
for a project's 2022 scaffold vs. its 2025 rewrite isn't a meaningful thing
to ask of a human rater, and keeping one project-level scope value applied
identically to every burst would just reintroduce the same
hidden-the-real-story problem the whole redesign exists to fix. Christophe
confirmed this explicitly (via AskUserQuestion) — scope is now **dropped
from the chart entirely**, not computed anywhere, not fed from anywhere.
**If asked "do we still need human estimation of feature complexity?" the
answer is no — it's fully obsolete for this chart**, not just temporarily
unused. (`scope` still appears as an ordinary English word in `repos.yaml`'s
notes — e.g. "enough scope to count as a project" — that's unrelated, not a
leftover reference to the old rating field.)

**Each burst ends in a circle**, radius sqrt-scaled (area-proportional) to
**LOC as of the end of that specific burst** — not current HEAD. Computed by
`scripts/compute_burst_loc.py`: for each repo contributing to a project,
find that repo's own latest commit at-or-before the burst's end date, check
it out detached, run the same cloc filter (`--exclude-lang` allowlist +
`manual_excludes.py`'s vendor/generated-file excludes) `gather_data.py`
already used, sum across repos, then restore the repo to its original ref.
Verified afterward (`git status --short --branch` across every clone) that
nothing was left detached. This is slow (one checkout+cloc per repo per
burst) but is the only way to make `bwv1`'s 22 LOC and `bwv2`'s 13,026 LOC
show up as genuinely different points in time rather than one blended
total.

**Fixed a real double-counting bug in this, 2026-10-15**: when a project has
a contributing repo that stops receiving commits partway through (e.g.
`cthiebaud/ciaccona`, frozen since 2023-05-24 once `musicollator/ciaccona`
took over), "that repo's latest commit at-or-before the cutoff" resolves to
the *same* frozen SHA for every later burst — so its full static snapshot
was getting re-added to every subsequent burst's LOC total, not just the
first one after the freeze. Caught by Christophe noticing `ciaccona3`'s
LOC/day (769.7) was wildly out of line with everything else, and its
end-LOC (20,936) was suspiciously close to `ciaccona2`'s (20,624) despite
38 commits over 27 days vs. 1,124 commits over 115 — his hypothesis was
"probably a copy of ciaccona2," which turned out not to be quite right
(the actual commits in that window are genuine small edits, 6 new
performers added) but correctly flagged that *something* was wrong.
Fixed by tracking each repo's already-counted SHA per project, across
bursts in chronological order, and only re-running checkout+cloc when that
SHA has actually changed since the last burst — a frozen repo's LOC now
counts once, in the first burst after it stops moving, not forever after.
`ciaccona3` went from 20,936 to 11,941; `ciaccona4` from 20,538 to 11,543.
The same general fix also caught an analogous case in `music`
(`cthiebaud/vinyl` stopped changing after `music2`; `music3`/`music4` had
been re-counting it too — 1,620→337 and 5,068→3,785 respectively). If a
future burst's LOC/day looks implausible relative to its neighbors, this
exact mechanism is the first thing to check.

**Color**: one hue per **project** (not per burst — see "Color assignment"
below, same golden-angle method as before, now stepping through unique
projects instead of individual rows), so a multi-burst project's rows still
visually read as "one project, several episodes," not as unrelated colors.
Lightness still darkens with that **burst's own** AI-attribution %, so two
bursts of the same project can still visibly differ in shade.

**The per-day trail bars are centered on the commits/day line** (extend
`h/2` up and `h/2` down), not growing upward from it — and the burst's
circle is drawn **before** the bars in SVG paint order, so bars always
paint on top. Christophe explicitly flagged "trails must not be hidden by
circles" mid-session; this ordering satisfies that. Labels/leader-lines
point at the circle (burst **end**), not the burst start.

**Known gap, disclosed in the chart's own footer**: `aiPct` is not (yet)
re-measured per burst — every burst currently inherits its parent project's
one blended value, which is actively misleading for `bwv1` specifically
(2022, predates Claude Code entirely) showing `bwv2`'s blended 3.4%. This is
the next piece of open work — see "Open / unfinished work" below.

### Superseded design (kept for history)

The original design (one row per whole project, y-axis = `scope / active_days`)
used:
- **X position & span** = real calendar start→end dates of the *whole
  project* (now: of each *burst*).
- **Y position** = `scope / active_days`, where scope was Christophe's own
  subjective 1–5 rating of feature scope (now: `commits / active_days`,
  objective, no human rating involved).
- **Line thickness** = total commit count (sqrt-scaled) — unchanged,
  still used (now per burst).
- **Color** = one hue per project, lightness darkened by AI-attribution % —
  unchanged in spirit, now grouped per project across that project's bursts
  rather than assigned per row.

LOC was considered for the y-axis early on and rejected (see "Rejected
approaches" below) — scope was the stand-in for "effort," now replaced by
the objective `commits/day` per burst, which sidesteps the original
objection entirely (no subjective rating needed at all now).

### Active-days / burst-clustering methodology (important, non-obvious)

"Lifespan" is not `last_commit − first_commit`. Real hobby projects have long
idle gaps (months, sometimes years) that shouldn't count as "active
development." The method: cluster commit timestamps by gap (120-day
threshold). In the superseded design, each project's clusters were *summed*
into one project-level active-days total. In the current design, **each
cluster is kept as its own burst** instead. Either way, the clustering
itself is immune to the arbitrary choice of gap length (120 days vs. 90 vs.
180 barely changes which commits land in which cluster) because it's
grouping genuine work episodes rather than picking one global span.

Implemented in [scripts/gather_data.py](scripts/gather_data.py) as
`active_days()` (project-level sum, superseded design) and
[scripts/compute_bursts.py](scripts/compute_bursts.py) (per-burst, current
design — same clustering rule, kept separate instead of summed).

### Hidden-branch scanning (added 2026-10-15 — "branches should not be overlooked")

Every pipeline script (`compute_bursts.py`, `lines_changed_by_day.py`,
`compute_burst_loc.py`, `compute_burst_aipct.py`) previously ran `git log`
with no explicit ref, which silently reads only the checked-out default
branch — any real work sitting on an unmerged or disconnected branch was
invisible. Caught when Christophe asked why `covid`'s commit history
"looks gone" for the first half of 2020, which he specifically remembered
as the actual project start. Answer: it wasn't gone, it was on
`usa-covid-aequologica-net/usa.covid.aequologica.net`'s `backup` branch —
148 commits, 2020-06-18 → 2020-12-21, with **no common ancestor with
`master`** (`git merge-base` empty, `--is-ancestor` false — a genuine
from-scratch restart on 2020-12-20, not just an unmerged branch). Christophe's
memory was right; `master` alone understated his covid start by ~6 months.

An audit of every included repo's non-default branches
([scripts/audit_hidden_branches.py](scripts/audit_hidden_branches.py))
found the branch lists cluttered with two confirmed-noise categories, not
auto-excluded but flagged for eyeballing: `dependabot/*` (bot-authored
dependency bumps, 1 commit each, never merged) and `gh-pages` (confirmed,
twice, by reading actual file contents, to be deploy-script build output —
hashed bundle filename renames, `manifest.json`, `.output/` artifacts —
even though git credits Christophe as author, since he's the one who ran
the deploy script). Six branches survived as real, human-authored,
non-build-output work and were added as a curated `extra_refs:` list per
repo entry in [repos.yaml](repos.yaml) (deliberately curated, not an
automatic `git branch --all` scan, so the noise categories above can never
sneak back in): `usa.covid.aequologica.net`'s `backup` (above),
`cthiebaud/ciaccona`'s `dev`/`dev2` (16 commits, Apr/May 2023, never merged
into `main`), `cthiebaud/vinyl`'s `no_color_no_font` (58 commits spanning
2024-01-13 → 2026-09-27, confirmed genuine hand-written feature work, not
build output), `cthiebaud/gear`'s `freeform-layout` (4 commits,
2026-09-02/03), `cthiebaud/truth`'s `production`, and
`sangiovannilipioni.github.io`'s `nuxt3` (the latter two trivial,
1 commit each, included for completeness).

[scripts/repo_refs.py](scripts/repo_refs.py) is the shared helper
(`refs_for(owner, repo)` → `["HEAD"] + extra_refs`) every pipeline script
now calls instead of an implicit ref-less `git log`; commits are merged
and deduped by SHA across refs. For `compute_burst_aipct.py`, which needs
`disclosure scan` to read the *checked-out* tree (it doesn't take a ref
argument), each extra ref is checked out temporarily, scanned, then the
repo is restored to its original ref — same checkout/restore pattern
`compute_burst_loc.py` already used for historical LOC snapshots.

Effect on the chart: `covid` now starts 2020-06-15 (was 2020-12-20,
367 commits vs. 216); `ciaccona2` gained 16 commits (1,124 → 1,140);
`music3`/`music4` and `gear` picked up smaller bumps from their own
extra refs. Re-run order after any `extra_refs` change: `compute_bursts.py`
→ `compute_burst_loc.py` → `lines_changed_by_day.py` →
`merge_daily_series.py` → `compute_burst_aipct.py`, then regenerate
`index.html`'s `data` array and `dailySeries` object from the resulting
JSON files (no dedicated generator script exists yet — see "Open /
unfinished work").

### LOC methodology

`cloc . --exclude-lang=SVG,JSON,YAML,CSV,XML --json`, run against the
checked-out working tree directly (not `cloc --git <ref>` — confirmed
`cloc`'s `--fullpath` flag is silently ineffective in `--git` mode, so
`--git` mode can't apply the manual excludes below; a direct directory scan
on the already-checked-out clone is equivalent and `--fullpath` works
correctly there), **plus** a maintained manual exclude list
([scripts/manual_excludes.py](scripts/manual_excludes.py)) of vendor
libraries and generated/data-dump files the language-level filter can't
catch — discovered by auditing each repo's top-LOC and top-churn files
(`scripts/audit_loc_top_files.py`, `scripts/top_files_by_churn.py`).
Confirmed real confounds this way: vendored jQuery/Bootstrap/Handlebars/
Prism.js, an ANTLR-generated parser checked into `src/main`, an
auto-generated GraphQL schema dump, auto-generated `docs/timings/*.js`
files, and several word-list/fixture data files (`isbn*.txt`,
`greeks.txt`, a pipe-delimited building-survey export, a raw FFT
wavetable). Also caught and fixed a real bug: a 165,000-"line" PDF that
git's binary-detection heuristic failed to flag as binary, counted as
"lines of code" until the LOC-counting logic was switched from a 4-extension
blocklist to a `cloc`-recognized-language allowlist.

`XML` was added to the exclude-lang list 2026-10-15: `bwv543`'s MusicXML
score files play the same "content, not code" role `SVG` already plays for
every other `bwv`/`ciaccona` repo.

In the superseded (project-level) design, LOC was a **current-snapshot**
measure (today's HEAD), shown in the tooltip/table for context but not used
on either chart axis. In the current (burst) design, LOC is no longer a
snapshot — it's computed **as of the end of each specific burst**
(`compute_burst_loc.py`, see above) and directly drives each burst's circle
size, so it's now one of the chart's primary visual encodings, not a
secondary one.

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

**Currently measured per project, not per burst** — this is the biggest
known honesty gap in the current (burst) design, already disclosed in the
chart's own footer caveat. `disclosure` itself isn't installed in this
environment right now (its `/tmp` install from an earlier session is
ephemeral and was gone by the next session) — reinstalling it
(`GOBIN=/tmp/disclosure-bin go install github.com/chaoss/disclosure@latest`,
needs a reasonably current Go) and re-running it scoped to each burst's own
commit range, then updating `index.html`'s `data` array and the footer
caveat paragraph, is the next piece of open work — see below.

Caveat baked into the chart's footer regardless: disclosure only catches
*disclosed, git-level* traces, so chat-based AI use with no trailer or tool
mention left in the repo (manually typed/pasted) is invisible to it — true
involvement may be higher than shown, especially before mid-2025.

`aiPct` is **not** computed by any of the `gather_data.py`/`compute_burst_*`
scripts — it comes from ad hoc `disclosure` runs, hand-entered into
`index.html`'s `data` array (currently per-project; per-burst is the open
task).

### Color assignment (fixed a real bug already — don't reintroduce it)

Hue is assigned by **golden-angle stepping** (`i * 137.50776° mod 360`)
through **projects** (not individual burst rows — changed 2026-10-15),
sorted by that project's *earliest* burst start date. Every burst of the
same project shares its project's hue; only lightness (driven by that
burst's own `aiPct`) varies within a project's bursts. An earlier greedy
"maximize distance from the one time-overlapping neighbor" approach was
tried and **collapsed to just two alternating hues** (verified: ciaccona/
sangiosleague/covid/parimagine all landed on hue 0°, sangiovannilipioni/bwv/
earthlydelights all on 180°) — because most items only conflict with one
immediate predecessor, so "pick the exact opposite" oscillates binary
instead of spreading. Golden-angle stepping has no small-integer
resonances, so time-adjacent indices land far apart in hue and stay that
way — same principle as phyllotaxis/sunflower seed placement. Verified
worst-case hue separation among any time-close pair: 52.5°, vs. 0° before.

Lightness: `L = 68 - 36 * sqrt(aiPct/100)` (sqrt so even a few % of
AI-attribution shows a visible step, rather than needing to approach 100%).

## Projects in scope, and why others aren't

Final 14: **parimagine, earthlydelights, covid, sangiosleague,
sangiovannilipioni, ciaccona, bookshelves, aletheia, bwv, mundial, gear,
music, klam, openmozart.** These 14 now split into **22 bursts** in the
current chart (see "The burst redesign" above) — e.g. `bwv` → `bwv1` +
`bwv2`, `ciaccona` → `ciaccona1..4`. The full repo-to-group mapping,
including every repo's `status` (`include`/`exclude`) and the reasoning
behind each, is the **canonical source of truth** in
[repos.yaml](repos.yaml) — don't re-derive this list from memory, read the
file. It also carries each included project's live public site URL
(`site:` field, `null` where none is live — checked against GitHub's own
Pages API, not just DNS, since a domain can resolve without actually being
*your* content anymore, see "music" below for one real example of exactly
that).

**`music` was added mid-session on 2026-10-15**, reversing an earlier
exclusion ("too tiny") — merging in `cthiebaud/vinyl` gave the combined
group enough scope to count. **`klam` and `openmozart` were added the same
day, by a different route**: once the chart became burst-based, "too tiny
as a whole project" stopped being the right question for a project that was
excluded purely on size — both have one real, substantial burst (checked
against authorship and vendor-content confounds the same way every other
repo is), bigger than the smallest burst already in the chart. The
**sibling investigation of `openricard`** found an even more intense burst
(27.1 commits/day, the most intense of any excluded repo) but it was **not**
added — Christophe's call, the "joke project" verdict stands despite the
burst intensity; don't re-add without asking again. **`emugnier`'s original
"too tiny" reasoning was simply wrong** — it has a real, substantial burst
too, but turned out to be the "Mugnier & Thiebaud" joint site already
excluded under the `mugnierandthiebaud` org, which is the actual reason it
stays out. If you find older notes anywhere saying "11 projects" or "12
projects," or listing `klam`/`openmozart` as excluded, those are stale;
`repos.yaml` is correct.

**The lesson generalized**: "too tiny/not worth it" was always a
whole-*project* verdict. Once the chart's unit became the burst, that
verdict needed re-checking for every repo excluded on size grounds — some
reversed (`klam`, `openmozart`), one didn't despite a strong burst
(`openricard`, excluded for a different reason entirely), and one revealed
its *real* exclusion reason had never been "too tiny" at all (`emugnier`).
Exclusions grounded in something other than size (infra/meta, joke intent,
professional/course work, forked/not-his-authorship, sites built for other
people) don't automatically get revisited just because the unit changed —
check what the *actual* reason was before assuming burst reframing applies.

Explicitly excluded, per Christophe's direct instructions — don't re-add
without asking (see `repos.yaml` for the complete list with reasons;
highlights):
- **iroif, aequologica, cthiebaud.github.io** — not true "projects" (infrastructure/meta); re-checked 2026-10-15 under the burst model, all three have real bursts but the infra/meta nature is unaffected by that
- **openricard** — a joke project; re-investigated 2026-10-15 (see above), not added
- **emugnier** — the "Mugnier & Thiebaud" joint site, same as the `mugnierandthiebaud` org (not actually "too tiny," see above)
- **hat** — a professional assignment, not hobby work. **Confirmed 2026-10-15: no repo named or containing "hat" exists anywhere accessible to Christophe's GitHub account** (`gh search repos`, global search, and a re-check of all 14 orgs all came back empty) — it genuinely isn't recoverable from GitHub. Christophe has a local copy from his own drive; whether it's usable depends on whether it has its own `.git` history, since this entire pipeline is git-log-driven. If it doesn't, there's nothing to compute bursts/LOC/aiPct from.
- **athenaeum** (the whole `athenaeum-brew` org) — a side project done *on* a professional course, not hobby; re-checked 2026-10-15, two real bursts exist but the course-work nature is unaffected by the burst model
- **~25 other repos** — personal forks of 3rd-party code, starter-template clones, scratch/test repos, and sites built for other people (`carolethomas`, `mugnierandthiebaud`, `eric-mugnier`) rather than Christophe's own hobby work — see `repos.yaml` for the full per-repo reasoning.

`parimagine` and `earthlydelights` were almost missed entirely in the
original (pre-`repos.yaml`) inventory — Christophe noticed their absence
himself and they were folded in. If auditing for completeness again, cross-
check both personal repos **and GitHub orgs** via the GitHub Pages API
(`scripts/check_pages.py` — queries every known repo's Pages config
directly rather than inferring from DNS, which caught a real miss:
`sangiovannilipioni`'s actual configured custom domain was
`sangiovannilipioni.net`, not the `.github.io` URL originally assumed —
and separately, that domain turned out to have been taken over by another
team and now serves unrelated content, confirmed by Christophe directly;
no automated check could have caught *that* part).

Old pre-migration repos were folded into their modern successor's numbers
(not kept as separate chart entries, and not treated as separate bursts
either — a migration isn't a 120-day idle gap): `cthiebaud/ciaccona` →
`ciaccona`, `cthiebaud/bwv543` → `bwv`.

## Rejected approaches (don't redo these — they were tried and abandoned)

- **Scope/day as the y-axis, one row per whole project** — superseded
  2026-10-15 by the burst redesign (commits/day per burst) — see above. The
  underlying objection to LOC that originally motivated subjective "scope"
  still holds (*"LOC is a measure of effort, but a much better one would be
  'features.' One can be so efficient to output more feature with less
  lines."*) — `commits/day` sidesteps the whole question rather than
  answering it: it doesn't claim to measure "features," only rhythm of
  activity, which is what this chart is actually about now.
- **A single shared bucket size for the sparkline bars, derived from the
  full chart's time range** — tried 2026-10-15: correct in principle (true
  cross-project comparability, a bar meaning the same timespan everywhere),
  but using the full ~13-year default view as the divisor made it
  absurdly coarse (365-day buckets), collapsing every short burst to a
  flat block. The actual fix needed no bucketing logic at all: the full
  per-day dataset is only ~600 points total across every project, so each
  real day is simply rendered as its own bar, always — trivially uniform
  (always exactly 1 day) without deriving anything.
- **Grep for AI keywords in commit messages** — see AI-attribution section above.
- **Homegrown AI-content-detection heuristics** (em-dash frequency, buzzword
  patterns in diffs) — explored, then explicitly rejected by Christophe in
  favor of using the real `disclosure` tool.
- **Greedy conflict-based hue assignment** — see Color assignment above.
- **A single fixed gap-threshold "largest cluster" lifespan** — rejected in
  favor of the gap-clustered sum (superseded design) / gap-clustered rows
  (current design), for robustness to the threshold choice.

## Mobile responsiveness (added 2026-10-15)

Desktop/tablet behavior is unchanged. On any screen where the **smaller** of
width/height is ≤640px (catches landscape phones too — width-only
breakpoints miss them, confirmed on a real device test):
- The subtitle/legend/footer collapse into a tap-to-expand `<details>`
  (`#about`), closed by default on mobile, forced open on desktop via JS
  (`aboutDetails.open = !mobile`) — the `<summary>` itself is CSS-hidden on
  desktop so it reads as always-visible plain text there.
- Custom wheel-zoom/drag-pan is disabled (it fights native touch
  scroll/pinch) in favor of native touch behavior (`touch-action: auto`).
  `Reset zoom`/`Maximize graph`/the zoom hint are hidden; `Table view`
  stays available everywhere.
- **Portrait only** additionally gets a **transposed layout**
  (`renderPortrait()`): time runs top-to-bottom instead of left-to-right,
  since a 13-year timeline fits a tall narrow screen far better than
  squeezed into its width. No zoom at all here — the page just renders tall
  enough (`PX_PER_DAY` constant) to be directly readable via normal page
  scroll. Landscape mobile keeps the normal horizontal layout, just pinned
  to full extent with the zoom UI hidden.

**A real, now-fixed bug worth knowing about**: there was no
`<meta name="viewport">` tag at all for most of this work. Without it,
mobile browsers default to a ~980px desktop-width "layout viewport" and
shrink the whole page to fit the screen — which also means
`window.innerWidth` and the CSS media queries both read ~980px, so *none*
of the mobile-specific code above ever activated, even though it was
correct. This was **invisible to Playwright testing** using a plain
`viewport: {width, height}` context, because that sets the layout viewport
directly, bypassing the exact mechanism a real phone hits. **Any future
mobile testing in this project must use real device emulation**
(`playwright.devices["iPhone 13"]` or similar, with `is_mobile: true`), not
a bare viewport size — confirmed the bug only reproduces that way.

## Deployment

Live at **https://stats.cthiebaud.com**, via GitHub Pages on
`github.com/cthiebaud/stats` (`main` branch, served from repo root,
`CNAME` file committed at root). DNS: a `stats` CNAME record at Gandi
pointing to `cthiebaud.github.io`, matching the pattern every other
`*.cthiebaud.com` project site already uses. HTTPS cert provisioning is
automatic on GitHub's side once DNS resolves (can take up to ~an hour;
`gh api -X PUT repos/cthiebaud/stats/pages -F https_enforced=true` returns
`"The certificate does not exist yet"` until it's ready — that's normal,
not an error to chase).

A local nginx dev server block also exists (port 8090, see
`/usr/local/etc/nginx/nginx.conf`, same per-project-port-number pattern as
every other project on this machine) serving this folder directly —
`nginx -s reload` after config changes.

While cloning/auditing this repo's own inventory, also found and reported
two **unrelated, pre-existing dangling DNS records** at the same registrar
(`questioneer` → a long-dead Azure app tied to the already-excluded
`athenaeum-brew/questioneer` course repo; `bwv1006.cthiebaud.com` → a
`cthiebaud.github.io` CNAME with no repo actually configured for that exact
custom domain) — both removed by Christophe. Not part of this project's own
scope, just surfaced as a side effect of the Pages-API cross-check above.

## Open / unfinished work

1. ~~Re-measure `aiPct` per burst, not per project.~~ **Done 2026-10-15** —
   see "AI-attribution methodology" above
   ([scripts/compute_burst_aipct.py](scripts/compute_burst_aipct.py)).
   `bwv1` correctly shows 0%, not `bwv2`'s old blended 3.4%.
2. **"vert axis is 'efficiency of dev'"** — Christophe's own phrasing from
   a round of feedback on the *superseded* (scope/day) design. The y-axis
   is now `commits/day`, an objective measure, not `scope/day` — this
   question may no longer apply the same way, but hasn't been explicitly
   revisited since the burst redesign. Worth a quick check rather than
   assuming it's resolved by the axis change alone.
3. **`hat` may still be investigable** if Christophe's local copy (from his
   own drive, not GitHub — confirmed unlocatable there, see "Projects in
   scope" above) turns out to have its own `.git` history. If it does, it's
   explicitly excluded anyway (professional assignment, not hobby) — but if
   he ever asks to revisit that verdict, check for `.git` first before doing
   anything else, since this entire pipeline is useless without real commit
   history to work from.
4. ~~Hidden-branch history was being silently dropped (HEAD-only `git
   log`).~~ **Done 2026-10-15** — see "Hidden-branch scanning" above.
5. ~~`parimagine`/`earthlydelights1`/`earthlydelights2` (2013-2019) ate a
   third of the chart's horizontal space for 3 of 22 bursts.~~ **Done
   2026-10-15** — Christophe's call ("interesting, but make the graph
   poorly readable ... for little value"): excluded from the **chart only**
   via a per-row `chart: false` flag in `index.html`'s `data` array, feeding
   a derived `chartData` array that every chart-geometry calculation and
   both `render()`/`renderPortrait()` read from. `data` itself (and Table
   view, which reads it directly) is untouched — these three bursts are
   still real, still in `repos.yaml`, still fully visible in Table view.
   The chart's effective visible range now starts at `covid` (2020-06-15).
   No generator script exists for `index.html`'s `data`/`dailySeries`
   literals — they're assembled by hand (or an ad hoc one-off script) from
   `scripts/bursts.json` + `burst_loc.json` + `burst_aipct.json` +
   `project_daily_series.json` each time the pipeline is re-run; writing a
   real generator would remove a recurring source of transcription risk if
   this keeps happening.

## Repo / environment notes

- Source repos for the data pipeline are cloned into `clones/<group>/<owner>/<repo>`
  (gitignored) by [scripts/clone_repos.py](scripts/clone_repos.py), reading
  the group/repo list from `repos.yaml`. Re-run it if `clones/` is missing
  or stale; it skips repos that already have a clone present.
- `chaoss/disclosure` (Go) was installed via
  `GOBIN=/tmp/disclosure-bin go install github.com/chaoss/disclosure@latest`
  — required `brew install go` first since the system Go at `/usr/local/go`
  was an old 1.20.3. **`/tmp` installs don't survive between sessions** —
  confirmed gone in a later session, needs reinstalling whenever `aiPct`
  work resumes.
- Shell quirk (seen repeatedly across sessions on this machine): complex
  multi-line bash loops/heredocs sometimes fail with `command not found` for
  basic utilities despite a correct PATH. Workaround that always worked:
  write the logic as a standalone `.py` file and run `python3 script.py`
  instead of inline complex bash.
- **Multiple Claude Code sessions can be working on this same repo
  concurrently** (confirmed 2026-10-15: a sibling session, rooted in a
  different project's folder but editing these files via absolute path,
  did the entire burst redesign while this session was elsewhere). If a
  file looks like it changed since you last read it, that's not necessarily
  a bug — re-read it and verify against `git diff`/`git status` before
  assuming anything, same way you'd treat any other external change.

## Related, separate work (not part of this project)

`cthiebaud.github.io`'s `index.html` has its own, simpler "domains" table
(Peak Activity / Last Commit / Commits / LOC columns) with its own
maintenance script `scripts/update_domain_stats.py` in that repo — it covers
*all* of Christophe's public domains (now including `stats.cthiebaud.com`,
added 2026-10-15) and is unrelated to this chart's burst/AI-attribution
analysis, beyond sharing some methodology (the active-days gap-clustering
approach originated there). Don't conflate the two.
