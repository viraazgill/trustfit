Phase 1: the Trust Score engine. This is the heart of the project, so precision beats speed.

Read docs/02-trust-score-spec.md, config/trust_v1.yaml, `score_trust()` and its helpers in
reference/trustfit_reference.py, and reference/expected/subros_*.json.

Build `packages/trustfit_engine`:

1. `config.py`: load `config/trust_v1.yaml` into typed Pydantic models. Validate on load:
   category weights per role sum to 100; splits per category sum to 100 for every role (after
   role overrides); every parameter has rubric levels 0, 25, 50, 75 and 100. Fail loudly otherwise.
2. `models.py`: typed inputs (Evidence, Flag, Company, WhatIf) and the result model. Keep the result
   keys exactly as the reference produces them.
3. `trust.py`: `score_trust(company, role, config, as_of, what_if=None, fit=None)`, a pure function
   ported from the reference. No database, network or clock. Round half up only where the
   reference does.
4. `seed_io.py`: load `seed/subros.json` (full format) and `seed/demo_companies.json` (compact
   format) into Company models, resolving "today-Nd" dates against `as_of`.
5. `cli.py`: `python -m trustfit_engine trust seed/subros.json --role supplier --as-of 2026-10-24`
   prints the result JSON.

Tests (pytest, write them first):

- Golden: Subros as supplier == `subros_supplier.json`; the integrity what-if == `subros_supplier_whatif_integrity_clean.json`;
  all three roles == `subros_by_role.json`. Compare numbers to 4 decimal places.
- Rules: every case listed under "Rule tests" in docs/02-trust-score-spec.md.
- Properties (Hypothesis): the score always stays within 0-100; raising one verified level never
  lowers the base score; verifying one more parameter never lowers confidence.

Done when `make test` is green, `grep` finds no hard-coded weights in the engine code, and the CLI prints
87 / Amber / Watch for Subros. Commit "feat(engine): trust score v1 with golden tests".
Then show me the Subros summary and the test count.
