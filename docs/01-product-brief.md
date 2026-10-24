# TrustFit: product brief (hackathon build)

TrustFit helps a Japanese SME enter India by answering three questions in order: can this Indian company
be trusted (Trust Score), is it right for us (Fit Score), and what are we missing and who in India can
fill it (Gap Bridge).

## The problem

JETRO-PS-01 asks: "How can Japanese SMEs enter and expand in India more effectively and efficiently?"
A solution should help SMEs:

1. Understand Indian markets, target customers and regional differences across states
2. Identify, evaluate and verify reliable local distributors, JV partners and opportunities
3. Localize products, packaging, pricing and go-to-market models
4. Navigate regulatory, legal, taxation and operational requirements
5. Bridge differences in communication, negotiation and business culture
6. Build sustainable long-term local operations and trustworthy partnerships

TrustFit's Trust and Fit Scores answer ask 2 and ask 6. The Gap Bridge readiness check covers all six,
and turns each weak area into a list of trusted Indian companies that can fill it.

Evidence used in the pitch:

- 61.8% of responding Japanese manufacturers named India a promising market for the next 3 years,
  No. 1 for a 4th year (JBIC FY2025 survey, 209 of 338).
- 35.1% of Japanese firms not planning an overseas base rely on agents and partners instead, the top
  reason (JETRO FY2025 survey, n=998).
- 85.2% of surveyed firms are short of staff for overseas business (JETRO FY2025 survey, n=3,063).
- Impact HD booked about ¥1.93bn in 2019 on its Indian JV with Coffee Day Global (TSE filing, 26 Jan 2023).

## The three modules

| Module | Input | Output | Same for every SME? |
| --- | --- | --- | --- |
| Trust Score | Verified evidence on 37 parameters, flags, gates, trends | Score 0-100, band, confidence, verdict, outlook, "what turns it Green" | Yes (per role) |
| Fit Score | The SME's brief + the company's profile | Fit 0-100, fit confidence, Strong / Possible / Not a fit | No |
| Gap Bridge | The SME's 16 readiness answers + every company's Trust, Fit and capabilities | Gap severities, per-gap partner lists, an India entry team with coverage % | No |

## Principles

1. Trust decides eligibility; Fit justifies the visit. Fit and the Gap Bridge never raise a Trust verdict.
2. Only verified, fresh evidence counts. Missing data lowers confidence, never the score.
3. A strong area can't hide a weak one: knock-outs, caps, notches and the weakest-link rule protect the verdict.
4. The Gap Bridge only recommends companies that pass Trust: no knock-out, not Red, enough verified data,
   no competitor conflict.
5. Every number is explainable: each score lists its reasons and links to its evidence.
6. Show categories and weights; keep parameter rubrics confidential so companies can't game the score.
7. Call it a "score", never a "rating".

## Users

| Persona | Needs | Access |
| --- | --- | --- |
| SME decision-maker (Japan) | Shortlist of trustworthy, well-matched partners; what they're missing; what to check next | SME pages: brief, readiness check, matches, team, company reports |
| TrustFit analyst | Fast evidence entry with sources; instant re-scoring; what-if | Companies, evidence, flags, gates, trends, scores |
| Admin | Control of config versions and users | Everything |

## Scope

| Priority | What | Done when |
| --- | --- | --- |
| P0 | Trust engine + golden tests | Subros reproduces the deck: 87, Very strong, 62.25 verified, Amber, Watch |
| P0 | Analyst evidence entry + Trust report + what-if | The integrity what-if turns Subros Green at 90 on screen |
| P1 | Fit engine, SME brief, combined verdict | Demo SME results match `reference/expected/demo_gap_bridge_sorano.json` |
| P1 | Gap Bridge: readiness check, gap cards, per-gap lists, entry team | Team = Deccan + CertiPath + Nihon-India + Swift Cargo, 82% coverage |
| P2 | PDF report, Japanese toggle on SME pages, deployment, landing page | Demo runs from a public URL and offline |

Non-goals for the hackathon: automated scraping, company self-service sign-up, billing, monitoring
alerts, a public directory, consent-based add-on data (tier T3 uploads by companies).

## Demo data

- **Subros Ltd** is real. Its category results match the pitch deck; its parameter levels were
  reconstructed to reproduce them, so the data lead must confirm every level and source before the demo.
- **Sorano Instruments (Demo)** and the nine Indian companies in `seed/demo_companies.json` are
  fictional, labelled "(Demo)". They exist to show Fit and the Gap Bridge end to end.

## Demo story (5 minutes)

1. Trust on a real company: Subros as a supplier scores 87, Very strong, but Amber: Integrity is only
   32.5% verified and the verification gates are pending. Outlook: Watch.
2. What-if: integrity checks clean and gates passed: confidence 82.5, score 90, Green.
3. Switch to the SME: Sorano's readiness check shows critical gaps in market understanding, regulatory,
   and operations; partner verification is covered by TrustFit itself.
4. Matches: Deccan Instrumentation is a Strong fit (90) and Green. Western Flow is trusted (92, Green)
   but Not a fit: it represents a competitor. Konkan Trade Links is excluded by a knock-out (GST cancelled).
5. Entry team: Deccan + CertiPath (certification, tax) + Nihon-India Bridge (Japanese-English, market
   research) + Swift Cargo (customs, warehousing) cover 82% of Sorano's gap severity.
