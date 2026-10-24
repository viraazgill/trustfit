Phase 5: the Gap Bridge, our differentiator. The SME finds out what it's missing and gets trusted
Indian companies that are strong exactly there.

Read docs/04-gap-bridge-spec.md, config/gap_bridge_v1.yaml, and `readiness()`,
`capability_strengths()` and `gap_bridge()` in reference/trustfit_reference.py.

1. Engine: `bridge.py` ported from the reference: readiness and severities, capability strengths,
   eligibility with exclusion reasons, primary ranking, the greedy India entry team, what each member
   brings, gap status and per-gap shortlists.
2. Engine test: the full result for Sorano equals `reference/expected/demo_gap_bridge_sorano.json`
   (numbers to 4 decimal places). Add unit tests for the greedy stop rules (gain under 5, team at 85%,
   3 supporters max) and for every exclusion reason.
3. API: `PUT/GET /smes/{id}/readiness`, `POST /smes/{id}/bridge` (saved as a `bridge` score run).
4. Web:
   - wizard step 3 on `/sme/new`: the 16 questions grouped by the six JETRO asks, each with the 0-4
     scale labels; progress bar
   - `/sme/[id]`: a readiness radar (six axes labelled with the JETRO asks), and gap cards with
     severity labels (critical, significant, minor) and the tag "Covered by TrustFit" on R2
   - `/sme/[id]/matches`: primary partner ranking (Trust score + verdict, Fit + category, gap coverage %,
     match), then an "Excluded" section listing each excluded company with its reason
     (knock-out, competitor conflict, not a fit, Red, insufficient data)
   - per-gap shortlists: for each critical or significant gap, the top three companies with a one-line
     reason, such as "Certification support 100%, verified"
   - `/sme/[id]/team`: the India entry team as cards (role, Trust, what each brings), a coverage matrix
     heatmap (gaps x members), team coverage % as a progress ring, and uncovered gaps called out
5. Every recommendation links to the SME-safe company report.

Check with Playwright: Sorano's team is Deccan + CertiPath + Nihon-India Bridge + Swift Cargo at 82%,
Western Flow and Konkan appear under Excluded with the right reasons. Commit "feat: gap bridge".
Show me screenshots of the radar, matches and team pages.
