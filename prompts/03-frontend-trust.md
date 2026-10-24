Phase 3: the analyst screens and the Trust report.

Read the "Pages" table and design tokens in docs/05-architecture.md, and docs/06-demo-script.md part 1.

Build in `apps/web` (generate API types from the OpenAPI schema; use TanStack Query):

1. Login, plus an app shell in the deck's style (navy, blue, coral, paper; IBM Plex Sans and Mono).
2. `/companies`: table with name, type, latest score, verdict chip, confidence, and a "Fictional demo
   data" badge where `fictional` is true.
3. `/companies/[id]/evidence`: accordion per category A-H. Each row has a level picker that shows that
   level's rubric text (from `/config/rubrics`), a verified switch, source URL, source date, checked
   date, note, and a stale or missing badge. Saving re-scores (debounced 300 ms).
4. `/companies/[id]/flags`: knock-outs, caps, notches, fake reviews, gates V1-V3, the five trend signals.
5. `/companies/[id]`: the score panel:
   - role tabs; a big score with band; a confidence meter (60 and 40 marked)
   - three dimension cards (score, % verified, a warning under 50%)
   - eight category bars, pale when under half verified, with verified/total points
   - overrides applied: notches, cap, weakest-link limit, and which one bound
   - verdict chip with every reason; outlook with its five signals
   - "What turns it Green": the next checks list
   - a What-if drawer: tick parameters to set to 100 and gates to pass, preview the result, never save
     over real evidence; preset button "Integrity checks clean"
6. A shared `VerdictChip`, `ScoreCard`, `CategoryBar`, `DimensionCard` and `ConfidenceMeter`, reused later.

Check with Playwright: open Subros -> 87, Very strong, Amber, Watch; apply the "Integrity checks
clean" preset -> 90, Green; switch to JV partner -> 86. Take screenshots of each state and look at them.

Commit "feat(web): analyst trust screens". Show me the screenshots.
