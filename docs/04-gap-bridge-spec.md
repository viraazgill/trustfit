# Gap Bridge spec (v1)

The Gap Bridge finds what a Japanese SME is missing for India and recommends trusted Indian companies
that are strong exactly there. Numbers live in `config/gap_bridge_v1.yaml`; behaviour is defined by
`readiness()`, `capability_strengths()` and `gap_bridge()` in `reference/trustfit_reference.py`.

## 1. Readiness check (16 questions, JETRO's six asks)

Each answer is 0 Not started, 1 Early idea, 2 Partly done, 3 Mostly done, 4 Done and validated.

| Dimension | JETRO ask | Questions |
| --- | --- | --- |
| R1 Market understanding | Understand markets, customers, regional differences | R1.1-R1.3 |
| R2 Partner identification and verification | Identify, evaluate and verify partners | R2.1-R2.2 |
| R3 Localisation | Localize products, packaging, pricing, go-to-market | R3.1-R3.3 |
| R4 Regulatory, legal and tax | Navigate regulatory, legal, taxation, operations | R4.1-R4.3 |
| R5 Communication and business culture | Bridge communication, negotiation, culture | R5.1-R5.2 |
| R6 Sustainable operations | Sustainable operations and trustworthy partnerships | R6.1-R6.3 |

- readiness = mean(answers) / 4 x 100
- severity = min(100, (100 - readiness) x relevance[role_sought][dimension]); relevance in the config
- label: critical >= 60, significant >= 35, minor otherwise
- R2 is "covered by TrustFit": shown in the diagnostic, left out of partner coverage maths.

## 2. Capability strengths (0 to 1) per company, against this SME

| Source | Capabilities | Strength |
| --- | --- | --- |
| Verified Trust evidence | quality_certified (F3)*, regulatory_clean (A5)*, japanese_language (G4), foreign_partner_experience (G2), payment_reliability (mean of verified E1, E2)* | level / 100 |
| Fit attributes vs this SME | regional_reach (FT2)*, sector_customer_access (FT1)* | level / 100, x0.5 if unverified |
| Service network vs target states | after_sales_network | level / 100, x0.5 if unverified |
| Declared tags | market_research, contract_manufacturing, local_sourcing, engineering_localisation, certification_support, customs_clearance, tax_compliance, business_interpretation, warehousing_logistics | level / 100, x0.5 if unverified |

\* business partners only (a consultant's own ISO certificate doesn't localise the SME's product).

## 3. Coverage

Each gap needs capabilities with weights that sum to 1 (`gap_needs` in the config), for example
R4 = certification_support 0.35, customs_clearance 0.25, tax_compliance 0.2, regulatory_clean 0.2.

- Coverage of gap g by a team = sum over its needs of weight x (strongest member's strength).
  For one company, the team is just that company.
- Gap coverage % of a team = sum(severity_g x coverage_g) / sum(severity_g) x 100, over gaps except R2.

## 4. Eligibility (who can be recommended)

A company is excluded when any of these is true, and the reason is shown:
- Trust knock-out (not eligible)
- Trust status insufficient_data (confidence under 40)
- Trust verdict Red
- a blocking relation with one of the SME's competitors
- (business partners offering the sought role) Fit category Not a fit

Business partners are Trust-scored with the SME's sought role; service providers with the
`service_provider_trust_role` (distributor weights, a v1 assumption).

## 5. Outputs

1. **Primary partner ranking**: eligible business partners offering the sought role, ranked by
   match = 0.6 x Fit + 0.4 x gap coverage, then Trust score, then name.
2. **India entry team** (greedy maximum coverage): start with the top primary partner; then, up to 3
   times, add the eligible service provider with the largest gain in team gap coverage (ties: higher
   Trust, then name). Stop when the gain is under 5 points or the team reaches 85%.
3. **What each member brings**: the capabilities where that member is the team's strongest
   (ties go to the member added first), with the gap each serves.
4. **Gap status** for the team: covered (>= 0.5), partly covered (>= 0.25), not covered.
5. **Per-gap shortlists**: for each critical or significant gap, the top 3 eligible companies of any
   type with coverage >= 0.25 for that gap.

Every recommendation shows its Trust score and verdict, Fit (if any), and a one-line reason built
from its strongest capability, such as "Covers your Regulatory gap (critical): certification support
100%, verified".

## Golden numbers (Sorano Instruments, `reference/expected/demo_gap_bridge_sorano.json`)

| Dimension | Readiness | Severity | Label |
| --- | --- | --- | --- |
| R1 Market understanding | 41.67 | 70 | critical |
| R2 Partner verification | 12.5 | 87.5 | critical (covered by TrustFit) |
| R3 Localisation | 66.67 | 26.67 | minor |
| R4 Regulatory, legal and tax | 25 | 90 | critical |
| R5 Communication | 50 | 50 | significant |
| R6 Sustainable operations | 25 | 90 | critical |

| Company | Trust | Fit | Result |
| --- | --- | --- | --- |
| Deccan Instrumentation | 85 Green | 90 Strong fit | Primary partner (match 72.95, gap coverage 47.37%) |
| Western Flow Systems | 92 Green | 54 Not a fit | Excluded: represents Flowtek (Demo) |
| Sabarmati Process Controls | 59 Amber, provisional | 51 Possible fit | Second in ranking (match 39.45) |
| Konkan Trade Links | Not eligible | - | Excluded: A3 at 0 (GST cancelled) |
| CertiPath Compliance | 90 Green | - | Team, +17.22 (certification, tax) |
| Nihon-India Bridge Consultants | 92 Green | - | Team, +9.80 (Japanese language, interpretation, market research) |
| Swift Cargo & Customs | 66 Amber | - | Team, +7.58 (customs, warehousing) |
| Bharat Calibration Services | 92 Green | - | Per-gap lists (after-sales) |
| Lotus Market Insights | 80 Amber, provisional | - | Per-gap list R1 (market research) |

Team coverage: 81.96%. Gap status: R1 0.825, R4 0.95, R5 0.925, R6 0.825 covered; R3 0.15 not covered
(minor gap).
