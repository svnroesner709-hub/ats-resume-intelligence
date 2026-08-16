# Job Description Research Sweep — 2026-08-15

Implements the spec's "Job Description Intelligence Database": a corpus of real, current, publicly-available job postings, used to give the keyword database genuine Level C sourcing ("large aggregated corpus of current job postings") rather than resting entirely on Level E internal domain knowledge.

**Scope requested**: ~100 postings across Anduril, Rocket Lab, Impulse Space, SpaceX, Blue Origin, Boeing, and Hadrian, not limited to program management — engineering, manufacturing, quality, supply chain, GNC, avionics, and more.

**Honest yield**: 33 structured records in `sweep_2026-08-15.json` (27 full-text, 6 from search-index snippets of live postings), plus roughly 40 additional postings surfaced only as titles/short context during the sweep and not converted into structured records. All 7 companies are represented; coverage spans Program Management, Systems Engineering, Manufacturing Engineering, Quality Engineering, Supply Chain, Mechanical/Structures, Propulsion, GNC, Avionics/Electrical, Software, Test Engineering, and Industrial Engineering. This did not reach 100 — see "Why not 100" below — but it's a real, diverse, honestly-sourced sample, not a padded one.

## Methodology

1. `WebSearch` to locate each company's careers platform and individual job-posting URLs (not just the listing/board page — see below).
2. `WebFetch` on individual posting URLs to pull full text where the platform allows it.
3. Where full-text fetch failed, the `WebSearch` tool's own synthesis of indexed page content was used instead (tagged `extraction_method: "search_snippet"` in every record) — this is real content pulled from a live posting via the search engine's index, not fabricated, but it's a shorter excerpt than a full fetch.
4. Extracted terminology was cross-checked against the existing `keywords/*.json` categories; genuinely new terms were added, and existing terms independently confirmed in a real posting had their `source_confidence` upgraded from `"E"` to `"C"` with a `sources` array recording company, role, URL, and date. See `scripts/apply_jd_sweep.py` (repo root) for the exact, reviewable diff this produced.

## Why not 100: platform fetchability varied a lot

- **Reliably full-text fetchable**: Greenhouse-hosted boards (`job-boards.greenhouse.io/andurilindustries`, `.../rocketlab` — SpaceX is also on Greenhouse but its board redirected to its own JS site more often than not) and, unexpectedly, **Built In's company mirror pages** (`builtin.com/company/{slug}/jobs` → individual `builtin.com/job/...` pages) — these worked for Hadrian, Impulse Space, SpaceX, Blue Origin, Rocket Lab, and Boeing and became the primary source once discovered partway through the sweep.
- **Consistently blocked / JS-rendered, no usable static content**: Ashby (`jobs.ashbyhq.com/hadrian-automation` directly), Pinpoint (`impulsespace.pinpointhq.com` directly), Rocket Lab's own `rocketlabcorp.com` domain (403), and Blue Origin's/Boeing's own career sites for listing pages (all client-side rendered). The companies' *own* career sites were usually not directly scrapable even when a third-party mirror of the same posting was.
- **Boeing-specific**: individual `jobs.boeing.com/job/...` postings churn fast — a meaningful fraction of URLs surfaced by search had already 404'd (position filled/removed) by fetch time. This is a real characteristic of that board, not a tooling failure.
- Given this, continuing to grind for exactly 100 would have meant either (a) padding with repetitive titles from the same few reliably-scrapable boards, or (b) fabricating postings for the unfetchable platforms. Neither is acceptable under this project's "never fabricate" rule — 33 real structured records (plus the ~40 titles-only) was the honest stopping point for this pass.

## Reproducing or extending this sweep

Re-run `scripts/apply_jd_sweep.py` to re-apply the same additions idempotently. To add more postings: extend `sweep_2026-08-15.json` (or start a new dated file) with the same record shape, and add corresponding `upsert_term(...)` calls to a new version of the apply script. Prioritize the Built In mirror pages and Greenhouse-hosted boards first — they're the reliable channel this sweep found.
