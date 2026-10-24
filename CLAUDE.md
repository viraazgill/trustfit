# TrustFit

TrustFit helps a Japanese SME enter India (JETRO-PS-01, Thapar Japan Hackathon). It answers three
questions, in this build order:

1. **Trust Score**: can this Indian company be trusted? 37 parameters, 8 categories, 3 dimensions,
   role weights, overrides, confidence, a Green/Amber/Red verdict and an outlook. Same for every SME.
2. **Fit Score**: is it right for *this* SME? Six fit factors scored against the SME's brief, giving
   Strong fit / Possible fit / Not a fit. Different for every SME. Fit can lower a verdict, never raise it.
3. **Gap Bridge**: what is the SME missing, and who in India can fill it? A 16-question readiness check
   built on JETRO's six asks, gap severities, per-gap lists of trusted Indian companies that are strong
   where the SME is weak, and an "India entry team" (one primary partner + up to 3 service providers).

## Where things are

- `docs/01-product-brief.md`: what we build and why, users, demo story, scope
- `docs/02-trust-score-spec.md`, `docs/03-fit-score-spec.md`, `docs/04-gap-bridge-spec.md`: the rules
- `docs/05-architecture.md`: stack, repo layout, data model, API, pages
- `docs/06-demo-script.md`: the live demo, click by click
- `config/*.yaml`: EVERY number the engines use (weights, splits, thresholds, rubrics, vocabularies)
- `seed/`: Subros (real company) + the fictional demo SME and nine fictional Indian companies
- `reference/trustfit_reference.py`: the reference implementation; `reference/expected/*.json` are golden outputs
- `prompts/`: the phase-by-phase build prompts (the humans paste these)

## Stack

Next.js (App Router, TypeScript, Tailwind, shadcn/ui, Recharts) in `apps/web`; FastAPI + Pydantic v2 +
SQLAlchemy 2 + Alembic in `apps/api`; pure Python scoring package in `packages/trustfit_engine`;
PostgreSQL 16; Docker Compose for local dev.

## Non-negotiable rules

- **The engine is pure and deterministic.** No database, network or clock inside
  `packages/trustfit_engine`. The scoring date is an argument (`as_of`). Same inputs + same config = same output.
- **No magic numbers.** Weights, splits, thresholds and labels come from `config/*.yaml`. Never change a
  config value unless a human asks; if a test fails, fix the code, not the config or the golden file.
- **Golden tests must pass.** The engine must reproduce `reference/expected/*.json`
  (compare numbers to 4 decimal places). `python reference/trustfit_reference.py --check` must stay green.
- **Round half up for display** (82.5 shows as 83). Keep full precision until the final step.
- **Missing is not zero.** Unverified or stale evidence stays out of the score and lowers confidence.
- **Confidential rubric.** `rubric` and `where_to_check` text, analyst notes and fraud rules are for
  analyst/admin roles only. Viewer (SME) endpoints and reports return categories, weights, scores and reasons only.
- **Words matter.** Say "score", never "rating" (SEBI regulates credit rating agencies). Every SME-facing
  report shows: "TrustFit Score is not a credit rating or investment advice."
- **Fictional data stays labelled.** Demo companies keep "(Demo)" in their names and `fictional: true`;
  the UI shows a "Fictional demo data" badge on them. Subros is the only real company in the seed.
- **No scraping** of pages behind a login or against a site's terms. Evidence is entered by an analyst with a source link.
- **Japanese text** in the UI must be marked for human review before the demo.

## Working style

- Read the relevant spec before coding. If two docs disagree, stop and ask; don't guess.
- Write tests first for engine rules. Keep functions small and typed.
- One phase per session. Finish with: tests green, lint clean, a short summary of what changed, then commit.
- Prefer boring, well-known libraries. No new dependency without saying why.

## Commands (update as the project grows)

- `make dev`: run web, API and Postgres
- `make test`: engine, API and reference checks
- `make seed`: load config, Subros and the demo data
- `python reference/trustfit_reference.py --check`: verify the golden outputs
