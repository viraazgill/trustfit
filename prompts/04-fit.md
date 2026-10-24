Phase 4: the Fit Score and the SME brief.

Read docs/03-fit-score-spec.md, config/fit_v1.yaml, and `fit_factor_levels()` and `score_fit()` in
reference/trustfit_reference.py.

1. Engine: `fit.py` with `score_fit(sme, company, fit_config)` ported from the reference. Pass its
   result into `score_trust(..., fit=...)` for the combined verdict. Load and validate
   `fit_v1.yaml` (vocabularies, thresholds, importance values).
2. Engine tests:
   - every `fit` and `fit_category` value in `reference/expected/demo_gap_bridge_sorano.json` (Deccan 90 Strong,
     Sabarmati 51 Possible, Western Flow 54 Not a fit, Konkan 57 Possible)
   - `subros_fit_denso_rival.json` (71, Not a fit through the competitor conflict)
   - unit tests per factor rule: thresholds at their exact edges, FT3/FT5 irrelevant rules, an
     unknown must-have blocks Strong fit, and Fit never raises a Trust verdict
3. API: SME CRUD (`/smes`), `GET /smes/{id}/fit/{company_id}` returning Fit + combined verdict.
4. Web:
   - `/sme/new`: wizard steps 1-2 (company profile, then the brief: sector, products, role sought,
     target states as primary/secondary chips, channels, volume, after-sales need, competitors,
     and per-factor importance with the role defaults pre-filled)
   - a Fit card on `/sme/[id]/company/[cid]`: six factor rows (importance, weight, level, verified),
     fit confidence, the category with its action ("Shortlist", "Gaps to close", "Skip, even if trusted"),
     and the combined verdict
   - in the Fit card, a competitor conflict says which brand and which relation

Check with Playwright: Sorano vs Deccan shows Strong fit 90; Sorano vs Western Flow shows Not a fit with
"represents Flowtek (Demo)". Commit "feat: fit score and SME brief". Show me screenshots.
