# Trust Score spec (v1)

The Trust Score rates one Indian company for one role (supplier, distributor or JV partner) on verified
evidence only. All numbers live in `config/trust_v1.yaml`; the behaviour is defined by `score_trust()`
in `reference/trustfit_reference.py`. Where this text and the reference disagree, the reference wins
and the text is a bug.

## Structure

- 37 parameters in 8 categories (A-H), grouped into 3 dimensions:
  - **Integrity** "Will they behave?": A Legal and regulatory standing, C Management and governance
  - **Financial** "Will they survive and pay?": B Financial health, E Payment and contract conduct
  - **Capability** "Can they deliver?": D Customer and market reputation, F Operational capability,
    G Cross-border readiness, H ESG and sustainability
- Each parameter scores one of five levels: 0, 25, 50, 75 or 100% (rubric text per level in the config).
- Data tiers: T1 public record, T2 peer and third party, T3 company-provided with consent.

### Role weights (points out of 100)

| Role | A | B | C | D | E | F | G | H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Supplier | 15 | 20 | 15 | 10 | 10 | 20 | 5 | 5 |
| Distributor | 15 | 20 | 10 | 15 | 20 | 10 | 5 | 5 |
| JV partner | 15 | 25 | 25 | 5 | 5 | 10 | 10 | 5 |

Parameter points = category weight x parameter split / 100 (splits in the config; distributors use
F3 10, F4 50, F5 10).

## Inputs

```text
company:  evidence {parameter_id: {level, verified, source_url, source_date, checked_at, note}}
          flags    [{type: knockout|cap|notch|fake_reviews, code, note, source_url}]
          gates    {V1|V2|V3: passed|pending|failed}      (absent = pending)
          trends   {signal: {direction: improving|stable|worsening, note}}
role:     supplier | distributor | jv_partner
as_of:    the scoring date (never read the clock inside the engine)
what_if:  optional {evidence: {parameter_id: level}, gates: {...}}: treated as verified, dated as_of
fit:      optional Fit result; can only lower the verdict
```

## Algorithm

1. **Evidence status** per parameter:
   - `missing`: no evidence
   - `unverified`: verified is false
   - `stale`: source_date more than 730 days before as_of, or (for parameters with `recheck_days`:
     A1, A3, A4, C1, E3) checked_at more than 30 days before as_of
   - `excluded`: D1 when a `fake_reviews` flag exists
   - `verified`: otherwise. Only `verified` parameters count.
2. **Knock-outs.** Any `knockout` flag, or a verified level 0 on a `knockout_at_zero` parameter
   (A1, A3, C1), ends scoring: `status = not_eligible`, `eligible = false`, `score = null`,
   `verdict = Red`, reasons list the knock-outs.
3. **Points.** For each parameter: `verified_points` = its points if verified, else 0;
   `earned_points` = points x level / 100. Category and dimension stats: points, verified_points,
   earned_points, `verified_pct` = verified / points x 100, `score_pct` = earned / verified x 100
   (null when nothing is verified).
4. **Confidence** = total verified points (out of 100). Below 40: `status = insufficient_data`,
   `score = null`, `verdict = Amber`, with next checks listed.
5. **Base score** = total earned / total verified x 100.
6. **Notches**: sum of the notch points (customer concentration over 70% -3, promoter-group company in
   default -5, strategic shareholder of 10% or more +3), clamped to +/-8.
7. **Weakest link**: weakest dimension score_pct (among dimensions with verified points) + 15.
8. **Cap**: lowest triggered cap (adverse or disclaimer audit opinion 50, going-concern uncertainty 60,
   asset attachment in the last 24 months 65); 100 when none.
9. **Final score** = round half up of min(base + notches, weakest + 15, cap). Record which limit bound.
10. **Band**: 85+ Very strong, 70+ Strong, 55+ Adequate, 40+ Weak, else Very weak.
11. **Provisional** if confidence < 60, or any dimension's verified_pct < 50.
12. **Verdict**, checked in this order:
    - **Red**: any gate failed; final < 55; or a Fit result is given and it is Not a fit (or Fit < 50).
    - **Amber**: confidence < 60; any dimension under 50% verified; any gate pending; fake reviews;
      55 <= final < 70; or a Fit result is given and it is a Possible fit.
    - **Green**: otherwise.
    Every triggered condition adds a `{code, text}` reason, so the UI can say exactly why.
13. **Outlook** from the five trend signals (revenue growth, operating margin, operating cash flow, cash
    conversion cycle, latest credit rating action): 3+ improving = Positive, 3+ worsening = Watch,
    else Stable; no trends = Not assessed. Outlook never changes the verdict.
14. **Next checks** ("what turns it Green"): unverified parameters in under-verified dimensions first,
    then the rest, each group by points (largest first), then pending gates.

## Output (keys of the reference result)

`company_id, role, as_of, weight_set, what_if, eligible, status, score, score_raw, band, confidence,
provisional, verdict, outlook, base_score, notches, notch_list, weakest_dimension, weakest_limit, cap,
cap_list, binding_limit, categories{A..H}, dimensions{integrity, financial, capability}, gates, reasons,
parameters{A1..H2: status, level, points}, next_checks`

The SME-facing report uses a filtered view: no `where_to_check`, no rubric text, no analyst notes.

## Golden numbers (Subros, supplier, as_of 2026-10-24)

| Output | Expected |
| --- | --- |
| Verified / earned points | 62.25 / 54.25 |
| Base score | 87.1486; final 87, Very strong |
| Category score % | A 100, B 86.8, C 75, D 92.9, E 75, F 92.6, G 89.1, H 82.5 |
| Verified points | A 3/15, B 19/20, C 6.75/15, D 3.5/10, E 4/10, F 17/20, G 4/5, H 5/5 |
| Dimensions (score / verified %) | Integrity 82.69 / 32.5, Financial 84.78 / 76.67, Capability 90.47 / 73.75 |
| Notches, weakest limit, cap | 0 (+3 and -3), 97.69, none |
| Verdict, outlook | Amber (Integrity under 50% verified; gates V1-V3 pending), Watch |
| What-if: A1, A3, A4, A5, C1, C2 at 100 + gates passed | Confidence 82.5, score 90 (90.30), Green |
| Other roles | Distributor 87 (confidence 57.25), JV partner 86 (63.25), both Amber |

Full outputs: `reference/expected/subros_supplier.json`,
`subros_supplier_whatif_integrity_clean.json`, `subros_by_role.json`.

## Rule tests the engine must also pass

- Any knock-out flag, or A3 verified at 0 -> not eligible, Red, no score.
- Confidence below 40 -> `insufficient_data`, no score.
- Cap 50 with a base of 80 -> final 50, verdict Red.
- Notches adding up to +11 -> clamped to +8.
- Weakest dimension 60 with a base of 85 -> final 75.
- A3 checked 31 days before as_of -> stale, excluded, confidence drops.
- fake_reviews -> D1 excluded and verdict at best Amber.
- A failed gate -> Red; a pending gate -> at best Amber.
- Property tests: the score always stays within 0-100; raising one verified level never lowers the
  base score; verifying one more parameter never lowers confidence.
