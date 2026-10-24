# Live demo script (about 5 minutes)

Before the demo: run `make seed` with `--reset`, open the app logged in as an analyst in one tab and
as the demo SME in another, and keep the backup video ready.

## Part 1: Trust on a real company (2 min)

1. Open **Subros Ltd**, role **Supplier**. Say: "A real, listed auto-component maker. 37 parameters,
   checked against public sources."
2. Point at the score: **87, Very strong**, but the verdict is **Amber**.
3. Open the reasons: "Integrity is 32.5% verified, under our 50% minimum. Verification gates pending."
   Point at the pale bars: Legal, Governance, Reputation and Payment conduct are under half verified.
4. Outlook **Watch**: margin, operating cash flow and the cash cycle are moving the wrong way.
5. Open **What-if** -> "Integrity checks clean" (A1, A3, A4, A5, C1, C2 at 100; gates passed):
   confidence **82.5**, score **90**, **Green**. Say: "Green only when we can check both money and integrity."
6. Optional: switch the role to **JV partner** -> 86. "Weights follow the role."

## Part 2: Fit and the Gap Bridge for an SME (3 min)

7. Switch to **Sorano Instruments (Demo)**, a fictional Osaka maker of flow meters looking for a
   distributor. Show the readiness radar: critical gaps in **Market understanding**, **Regulatory,
   legal and tax** and **Sustainable operations**; **Partner verification** is covered by TrustFit itself.
8. Open **Matches**:
   - **Deccan Instrumentation**: Strong fit 90, Trust 85 Green. "Right sector, right states, right channels."
   - **Western Flow Systems**: Trust 92 Green, but **Not a fit**: it represents a competitor. "Trusted isn't enough."
   - **Konkan Trade Links**: excluded, knock-out (GST registration cancelled). "We never recommend a knock-out."
9. Open **India entry team**: Deccan + **CertiPath** (certification, tax) + **Nihon-India Bridge**
   (Japanese-English business support, market research) + **Swift Cargo** (customs, warehousing).
   Together they cover **82%** of Sorano's gap severity. Localisation is a minor gap left uncovered.
10. Close: "Trust decides eligibility, Fit justifies the visit, and the Gap Bridge builds the team."

## If something breaks

- Network down: run locally with Docker Compose and seeded data.
- App down: play the backup video from the same script.
- A judge asks "how do you know the score is right?": open the golden test output; every number
  reproduces from config and evidence, and each evidence row links to its source.
