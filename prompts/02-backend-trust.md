Phase 2: the API and database for the Trust Score.

Read docs/05-architecture.md (data model, API, security) and CLAUDE.md again.

Build in `apps/api`:

1. SQLAlchemy models and an Alembic migration for `users`, `companies`, `evidence`,
   `evidence_history`, `flags`, `smes`, `score_runs`, with the constraints listed in the architecture
   doc: a level must be 0, 25, 50, 75 or 100, and a verified row needs `source_url` and `source_date`.
2. Seed command `python -m app.seed [--reset]`: loads Subros, the demo SME and the demo companies via
   the engine's `seed_io`, plus three users (admin, analyst, viewer) from environment variables.
3. JWT auth with roles admin / analyst / viewer.
4. Endpoints for companies, evidence (writes history), flags, gates and trends, `POST
   /companies/{id}/trust-score` (body `{role, what_if?}`, saves a `score_runs` row), `GET
   /companies/{id}/trust-report?role=`, `GET /config/public` and `GET /config/rubrics`.
5. `as_of = settings.SCORING_AS_OF or today`. Add `SCORING_AS_OF` to `.env.example`.
6. Viewer responses use separate schemas that cannot contain rubric text, `where_to_check`,
   evidence notes or source URLs of unpublished evidence. Add a test that fails if they ever do.

Tests (pytest, with a test database): scoring Subros through the API as supplier returns the golden
result; an analyst can update evidence and the score changes; a viewer gets 403 on analyst routes;
the viewer report has no rubric fields; a what-if run is saved with `is_what_if = true` and never
appears in viewer endpoints.

Done when `make test` and `make seed` work and the OpenAPI page at `/docs` lists every route.
Commit "feat(api): trust endpoints, auth, seed". Show me a curl session that scores Subros.
