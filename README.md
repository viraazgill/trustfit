# TrustFit build kit for Claude Code

Everything Claude Code needs to build TrustFit for the hackathon:

- the project rules (`CLAUDE.md`)
- the specs (`docs/`)
- every number (`config/`)
- the demo data (`seed/`)
- a reference implementation whose golden outputs already reproduce the pitch deck's numbers (`reference/`)
- seven paste-ready phase prompts (`prompts/`)

Build order: **Trust Score -> Fit Score -> Gap Bridge** (readiness check, partner lists, India entry team).

## How to proceed

**1. Set up**

- Create a private GitHub repo named `trustfit`.
- Copy everything in this kit into the repo root and commit it ("chore: add build kit").
- Open Claude Code in that folder. It reads `CLAUDE.md` automatically at the start of every session.

**2. Check the kit works**

`pip install pyyaml && python reference/trustfit_reference.py --check` must exit with no output.

**3. Build one phase per session, in order**

For each prompt:

- Start fresh with `/clear`.
- Switch to plan mode (Shift+Tab).
- Paste the prompt and review the plan.
- Let Claude Code build.
- Run `make test`, try the feature, then commit.

| Phase | Prompt | You get |
| --- | --- | --- |
| 0 | `prompts/00-kickoff.md` | Monorepo scaffold, CI, Docker |
| 1 | `prompts/01-trust-engine.md` | Trust engine passing the Subros golden tests |
| 2 | `prompts/02-backend-trust.md` | Database, API, auth, seed |
| 3 | `prompts/03-frontend-trust.md` | Analyst screens, Trust report, what-if |
| 4 | `prompts/04-fit.md` | SME brief and Fit Score |
| 5 | `prompts/05-gap-bridge.md` | Readiness check, matches, India entry team |
| 6 | `prompts/06-demo-polish.md` | Landing page, PDF, Japanese toggle, deploy, end-to-end test |

If time runs short:

- Phases 0-3 alone give a complete Trust demo.
- Phases 4-5 are your differentiators.
- Phase 6 is polish.

**4. Work in parallel.** While one person drives Claude Code:

- **Data lead:** confirm every Subros level and source in `seed/subros.json` (levels were
  reconstructed to match the deck's category results), and label the years for operating cash flow
  and cash cycle. If there's time, prepare one or two more real companies.
- **Pitch lead:** update the deck. Fit and the Gap Bridge move from "future scope" to "built". Add one
  slide on readiness -> gaps -> India entry team.
- **QA:** from phase 3 on, run `docs/06-demo-script.md` every day. Record the backup video after phase 6.

**5. Rehearse the demo twice**, once with the network off.

## Team split (four people)

| Person | Owns |
| --- | --- |
| 1. Engine lead | Phases 1, 4 and 5 (engine parts); reviews every change to scoring code |
| 2. Backend | Phase 2, the API parts of 4-5, deployment |
| 3. Frontend | Phases 3-5 (screens), landing page, Japanese toggle |
| 4. Data and pitch | Subros evidence, extra real companies, demo script, deck, backup video |

## Working well with Claude Code

- Keep one phase per session. A long session drifts.
- Don't accept edits to `config/` or `reference/expected/` you didn't ask for. If a golden test fails,
  the code is wrong, not the expected file.
- Commit after every green phase so you can roll back.
- Ask for screenshots and actually look at them.
- If it fails twice on the same error, stop it, paste the error, and ask for a different approach.
- To change a rule (say, a weight):
  1. Edit the YAML.
  2. Update `reference/trustfit_reference.py` if the logic changed.
  3. Regenerate with `python reference/trustfit_reference.py`.
  4. Review the diff of `reference/expected/`, then commit all of it together.

## Where your edge comes from (say these in the pitch)

1. **Built on JETRO's own six asks.** The readiness check mirrors the problem statement, question by question.
2. **More than vetting one partner.** TrustFit assembles an India entry team that covers the SME's gaps
   (82% in the demo) and names what is still uncovered.
3. **Honest uncertainty.** Confidence and provisional verdicts; missing data never counts as zero.
4. **Trusted isn't enough.** A Green company can still be Not a fit, for example when it represents a competitor.
5. **Explainable and reproducible.** Every number traces to config and a sourced evidence row, backed
   by golden tests.
6. **Responsible by design.** It's a score, not a rating; rubrics stay confidential; demo data is
   labelled fictional; personal data is minimised.
7. **A Japanese-language view** of the SME pages, if you build phase 6.

## Be ready for these judge questions

- **"Where do the weights come from?"** Version 1 expert weights by role, to be calibrated on a
  20-company pilot and a backtest. The Fit role defaults, readiness relevance and capability weights are v1
  proposals too.
- **"Is Subros's score real?"** The category results come from public sources (ICRA, investor
  presentation, Screener). The parameter levels must be confirmed by the data lead before the demo.
- **"How do you score service providers?"** With the distributor weights for now, which is a v1
  assumption.
- **"Isn't this a credit rating?"** No. It's a partner-selection score with a disclaimer, deliberately
  outside SEBI's credit-rating rules.

## Kit contents

```text
CLAUDE.md                         rules Claude Code follows in every session
README.md                         this guide
docs/01-product-brief.md          what we build and why, scope, demo story
docs/02-trust-score-spec.md       Trust rules + golden numbers
docs/03-fit-score-spec.md         Fit rules + golden numbers
docs/04-gap-bridge-spec.md        readiness, matching, entry team + golden numbers
docs/05-architecture.md           stack, repo layout, data model, API, pages
docs/06-demo-script.md            the 5-minute live demo
config/trust_v1.yaml              37 parameters with rubrics, weights, overrides, verdict rules
config/fit_v1.yaml                6 fit factors, importance, thresholds, vocabularies
config/gap_bridge_v1.yaml         16 readiness questions, capabilities, gap needs, team rules
seed/subros.json                  real company (levels to confirm)
seed/demo_sme_sorano.json         fictional Japanese SME
seed/demo_companies.json          nine fictional Indian companies
reference/trustfit_reference.py   reference implementation (Python + PyYAML)
reference/expected/*.json         golden outputs the real engine must match
prompts/00-06                     paste-ready phase prompts
```

## Running and deploying the app (added during the build)

### Local (also the offline demo fallback)

```bash
make install PYTHON=python3.12   # once: .venv, engine + API (+ [pdf] for PDF export), web deps
.venv/Scripts/python -m pip install -e "apps/api[pdf]" && .venv/Scripts/python -m playwright install chromium
make db seed                     # Postgres in Docker, migrations, seed (wipes and reloads)
make dev                         # API on http://localhost:8000/docs, web on http://localhost:3000
make test lint test-e2e          # engine + API + reference; ruff, ESLint, types, i18n; the demo in a browser
```

`docker compose --profile full up` runs Postgres, the API and the web app in containers instead.
Demo screenshots from `make test-e2e` land in `artifacts/demo/`.

### Hosting: web on Vercel, API on Render, Postgres on Neon

1. **Neon:** create a project and copy its connection string as
   `postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require`.
2. **Render:** New > Blueprint, pick this repo (`render.yaml`). Fill in the variables below. The container
   migrates and seeds an empty database on start. Copy the service's **Deploy Hook** URL.
3. **Vercel:** import the repo with **Root Directory `apps/web`** and set `NEXT_PUBLIC_API_URL`.
4. **GitHub secrets** (Settings > Secrets > Actions): `RENDER_DEPLOY_HOOK_URL`, `VERCEL_TOKEN`,
   `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`. CI then deploys on every push to `main`, only after the
   Python, web and end-to-end jobs pass. Without the secrets the deploy job just skips.

| Variable | Where | What |
| --- | --- | --- |
| `DATABASE_URL` | API | Postgres connection string (Neon in hosting) |
| `JWT_SECRET` | API | Long random string; Render generates one |
| `JWT_EXPIRE_HOURS` | API | Token lifetime, default 12 |
| `SEED_ADMIN_EMAIL` / `_PASSWORD` (also `ANALYST`, `VIEWER`) | API | The three seed users; set new passwords in hosting |
| `CORS_ORIGINS` | API | JSON list of web origins, e.g. `["https://trustfit.vercel.app"]` |
| `WEB_URL` | API | The web app the PDF printer opens (same pages the SME sees) |
| `SCORING_AS_OF` | API | Optional fixed scoring date (`YYYY-MM-DD`) for a reproducible demo; empty = today |
| `CONFIG_DIR`, `SEED_DIR` | API | Set by the Docker image; defaults to the repo's `config/` and `seed/` |
| `NEXT_PUBLIC_API_URL` | Web | The API base URL, e.g. `https://trustfit-api.onrender.com/api/v1` |

The admin's **Reset demo data** button (top bar) reloads the seed without touching users. Japanese
strings on the SME pages are listed for human review in `apps/web/messages/ja.REVIEW.md`.
