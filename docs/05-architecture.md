# Architecture (hackathon build)

The Next.js app only displays results; every score is computed by the FastAPI service calling the pure
`trustfit_engine` package, which reads `config/*.yaml`. Postgres stores companies, evidence, SMEs and
every scoring run.

## Stack

| Layer | Choice |
| --- | --- |
| Front end | Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts, TanStack Query |
| API | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Engine | `packages/trustfit_engine`: pure Python, PyYAML, Pydantic models for config |
| Database | PostgreSQL 16 (JSONB for profiles, capabilities, results) |
| Auth | JWT, roles admin / analyst / viewer |
| PDF | Playwright printing the report page (P2) |
| i18n | next-intl, English + Japanese for SME pages (P2) |
| Hosting | Vercel (web), Render or Railway (API), Neon (Postgres); Docker Compose locally |
| CI | GitHub Actions: engine tests, API tests, reference check, lint |

## Repo layout

```text
trustfit/
  CLAUDE.md
  config/                 trust_v1.yaml, fit_v1.yaml, gap_bridge_v1.yaml (read-only to code)
  seed/                   subros.json, demo_sme_sorano.json, demo_companies.json
  reference/              trustfit_reference.py, expected/*.json (golden outputs)
  docs/  prompts/
  packages/trustfit_engine/
    trustfit_engine/      config.py, trust.py, fit.py, bridge.py, models.py, cli.py
    tests/                test_trust_golden.py, test_trust_rules.py, test_fit.py, test_bridge.py, test_properties.py
  apps/api/
    app/                  main.py, db.py, models.py, schemas.py, auth.py, routers/, services/, seed.py
    alembic/  tests/
  apps/web/
    app/  components/  lib/  messages/ (en.json, ja.json)
  docker-compose.yml  Makefile  .github/workflows/ci.yml
```

## Config versions

For the hackathon, config versions are the YAML files in `config/` (v1). Every stored result records
the version it used. An admin editor for new versions is post-hackathon.

## Data model (Postgres)

| Table | Key columns |
| --- | --- |
| `users` | id, email, password_hash, role (admin, analyst, viewer) |
| `companies` | id (slug), name, fictional, type (business_partner, service_provider), roles_offered[], cin, nse_code, bse_code, msme_category, hq_state, description, profile JSONB, capabilities JSONB, gates JSONB, trends JSONB |
| `evidence` | company_id, parameter_id (A1..H2), level (0/25/50/75/100), verified, source_url, source_date, checked_at, note, updated_by, updated_at; PK (company_id, parameter_id) |
| `evidence_history` | the same columns + changed_by, changed_at (append-only) |
| `flags` | id, company_id, type (knockout, cap, notch, fake_reviews), code, note, source_url |
| `smes` | id, name, fictional, country, city, employees, description, sector, products[], role_sought, target_states JSONB, channels_needed[], volume_units_per_month, after_sales_need, competitors[], factor_importance JSONB, readiness_answers JSONB |
| `score_runs` | id, kind (trust, fit, bridge), company_id, sme_id, role, config_version, as_of, inputs_hash, is_what_if, result JSONB, created_by, created_at |

Constraints: level in (0, 25, 50, 75, 100); a verified evidence row needs source_url and source_date;
what-if runs are never shown on SME pages.

Seed loader: `python -m app.seed` expands the compact demo format (see `_format` in
`seed/demo_companies.json`), resolves "today-Nd" dates against today, and loads Subros, the demo
SME and the demo companies. A `--reset` flag wipes and reloads (used before every demo).

**Scoring date:** the API passes `as_of = settings.SCORING_AS_OF or today`. Golden tests use
2026-10-24. Demo companies use relative dates, so they stay fresh; Subros has real dates.

## API (`/api/v1`, JSON)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/login` | any | Email + password -> JWT |
| GET | `/config/public` | any | Categories, dimensions, role weights, fit factors, readiness questions (no rubrics) |
| GET | `/config/rubrics` | analyst | Parameter names, rubric text, where to check |
| GET/POST | `/companies` | viewer / analyst | List (latest trust score and verdict) / create |
| GET/PATCH | `/companies/{id}` | viewer / analyst | Profile, capabilities, gates, trends |
| GET | `/companies/{id}/evidence` | analyst | All 37 rows with status (verified, stale, missing) |
| PUT | `/companies/{id}/evidence/{param_id}` | analyst | Upsert one row (writes history) |
| POST/DELETE | `/companies/{id}/flags[/{flag_id}]` | analyst | Knock-outs, caps, notches, fake reviews |
| POST | `/companies/{id}/trust-score` | analyst | Body `{role, what_if?}` -> full result; saved as a run |
| GET | `/companies/{id}/trust-report?role=` | viewer | SME-safe report (no rubric, notes or where-to-check) |
| GET/POST | `/smes`, `/smes/{id}` | viewer | Create and edit an SME brief |
| PUT | `/smes/{id}/readiness` | viewer | Save the 16 answers |
| GET | `/smes/{id}/readiness` | viewer | Readiness and severities per dimension |
| GET | `/smes/{id}/fit/{company_id}` | viewer | Fit result + combined verdict |
| POST | `/smes/{id}/bridge` | viewer | Full Gap Bridge result: ranking, team, gap status, per-gap lists |
| GET | `/smes/{id}/report.pdf` | viewer | PDF of the SME's results (P2) |

Errors: `{"error": {"code", "message", "field"}}`; 422 validation, 403 role. The front end generates
TypeScript types from the OpenAPI schema.

## Pages

| Route | Who | What |
| --- | --- | --- |
| `/` | all | Landing: one-line pitch, "Try the SME demo" and "See a Trust Score" buttons |
| `/companies` | analyst | Table: name, type, latest score, verdict chip, confidence, "(Demo)" badge |
| `/companies/[id]` | analyst | Score panel: role tabs, big score, band, confidence meter, dimension cards, 8 category bars (pale under 50% verified), overrides applied, reasons, next checks, what-if drawer |
| `/companies/[id]/evidence` | analyst | Grid grouped A-H: level picker showing the rubric text per level, verified switch, source URL, dates, stale badge |
| `/companies/[id]/flags` | analyst | Knock-outs, caps, notches, gates, trends |
| `/sme/new` | SME | Wizard: profile -> brief -> 16-question readiness check |
| `/sme/[id]` | SME | Readiness radar (six JETRO asks), gap cards with severity labels, "R2 covered by TrustFit" |
| `/sme/[id]/matches` | SME | Primary partner ranking: Trust, Fit, gap coverage, verdict, plus excluded companies with the reason |
| `/sme/[id]/team` | SME | India entry team: members, what each brings, coverage matrix (gaps x members), team coverage %, uncovered gaps |
| `/sme/[id]/company/[cid]` | SME | SME-safe company report: Trust summary, Fit factors for this SME, reasons |

Design tokens (match the pitch deck): navy `#15213A`, blue `#1F4E8C`, coral `#E8875A`, paper
`#F5F3EE`, muted `#4A5568`; Green `#2F7D52`, Amber `#B7791F`, Red `#C0392B`; IBM Plex Sans and IBM Plex Mono.

## Security and compliance

- bcrypt passwords, 12-hour JWTs, HTTPS in deployment, secrets in environment variables.
- Viewer endpoints use separate response schemas that cannot carry rubric text or analyst notes.
- Store only the personal data a check needs; never show directors' personal data on SME pages
  (Digital Personal Data Protection Act, 2023).
- Every SME-facing page and PDF: "TrustFit Score is not a credit rating or investment advice."
