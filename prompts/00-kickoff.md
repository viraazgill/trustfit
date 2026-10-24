You're joining the TrustFit hackathon project. Start in plan mode: read before you write.

Read CLAUDE.md, docs/01-product-brief.md and docs/05-architecture.md. Skim config/, seed/,
reference/trustfit_reference.py and reference/expected/.

Then:

1. Tell me in five bullets what we're building, the build order, and the rules you must not break.
2. List any contradictions or gaps you find in the docs, each with your proposed fix. Don't fix them silently.
3. Propose the scaffold plan for the monorepo in docs/05-architecture.md, and wait for my OK.

After I approve:

4. Scaffold it:
   - `apps/web`: Next.js App Router, TypeScript, Tailwind, shadcn/ui, ESLint
   - `apps/api`: FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest
   - `packages/trustfit_engine`: an installable pure-Python package (pyproject), pytest
   - `docker-compose.yml` with Postgres 16; `.env.example`
   - `Makefile` with `dev`, `test`, `lint`, `seed` targets
   - `.github/workflows/ci.yml` running lint and tests
5. Leave config/, seed/, reference/, docs/ and prompts/ exactly where they are.
6. Make `make test` run `python reference/trustfit_reference.py --check` plus the (still empty) test suites.
7. Check: `make test` passes and `docker compose up` starts Postgres.
8. Commit: "chore: scaffold TrustFit monorepo".

Stop and show me the tree, the commands to run, and anything you need from me.
