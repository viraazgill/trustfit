# Fit Score spec (v1)

Fit rates the match between one Indian company and one Japanese SME's brief. Numbers live in
`config/fit_v1.yaml`; behaviour is defined by `score_fit()` and `fit_factor_levels()` in
`reference/trustfit_reference.py`.

## The SME brief

```text
sector                  one value from the sectors vocabulary, e.g. industrial_instruments
products                product tags, e.g. [flow_meters, water_quality_sensors]
role_sought             supplier | distributor | jv_partner
target_states           {primary: [...], secondary: [...]}
channels_needed         e.g. [industrial_b2b, epc_projects, government_tenders] (empty -> FT3 irrelevant)
volume_units_per_month  the volume the partner must handle
after_sales_need        none | basic | full (none -> FT5 irrelevant)
competitors             brand or company names to avoid
factor_importance       optional overrides per factor: must | important | nice | irrelevant
```

## The company profile

Each attribute is `{value, verified, source_url}`: `sectors, products, states, channels,
capacity_units_per_month, service_states, brand_relationships` (a list of `{brand, relation}`, where
relation is `owner | shareholder_10 | exclusive | represents | supplies`). A missing attribute makes
its factor unknown.

## Factors and levels (0, 25, 50, 75 or 100)

| Factor | Base weight | Level rule |
| --- | --- | --- |
| FT1 Sector and product experience | 25 | 100 same sector and a shared product; 75 a shared product, or same sector and a shared product family; 50 same sector; 25 a related sector; 0 none |
| FT2 Regional coverage | 20 | Weighted share of target states where the company operates (primary x2, secondary x1): >=0.9 100, >=0.7 75, >=0.5 50, >=0.25 25, else 0 |
| FT3 Sales and distribution channels | 20 | Share of needed channels the company uses, same thresholds |
| FT4 Capacity vs requirement | 15 | capacity / volume required: >=1.5 100, >=1.2 75, >=1.0 50, >=0.7 25, else 0 |
| FT5 After-sales and service | 10 | Weighted share of target states covered by the company's service network, same thresholds as FT2 |
| FT6 Competing-brand conflict (inverse) | 10 | A blocking relation (owner, shareholder_10, exclusive, represents) with a competitor -> 0; `supplies` -> 50; none -> 100 |

## Weights

1. Importance per factor = the role default (config `role_default_importance`) overridden by the brief.
   FT3 becomes `irrelevant` when no channels are needed; FT5 when after-sales need is `none`.
2. Effective weight = base weight x multiplier (must 2.0, important 1.0, nice 0.5, irrelevant 0).
3. Rescale the effective weights to sum to 100.

## Score, confidence, category

- **Fit score** = sum(weight x level) / sum(weight) over factors with a known level, rounded half up.
- **Fit confidence** = sum of weights of factors that are known AND whose attributes are verified.
- **Category**:
  - **Not a fit**: score < 50; or any must-have factor at 0; or a blocking competitor relation
    (FT6 = 0) unless the SME marked FT6 irrelevant.
  - **Strong fit**: score >= 70, every must-have factor known and at 50 or more, fit confidence >= 60.
  - **Possible fit**: everything else. List the gaps: factors below 50 or unknown.
- **Combined verdict**: pass the Fit result into `score_trust(..., fit=...)`. Not a fit -> Red;
  Possible fit -> Amber at best; Strong fit leaves the Trust verdict unchanged. Fit never raises a verdict.

## Golden numbers (Sorano Instruments brief, distributor role)

Distributor default importance: FT1 important, FT2 must, FT3 must, FT4 nice, FT5 important, FT6 must.
Effective weights: FT1 17.54, FT2 28.07, FT3 28.07, FT4 5.26, FT5 7.02, FT6 14.04.

| Company | Levels FT1-FT6 | Fit | Category |
| --- | --- | --- | --- |
| Deccan Instrumentation (Demo) | 100, 75, 100, 75, 75, 100 | 90 | Strong fit |
| Sabarmati Process Controls (Demo) | 75, 50, 25, 25, 25, 100 | 51 | Possible fit (FT3 must-have at 25) |
| Western Flow Systems (Demo) | represents Flowtek (Demo), a Sorano competitor -> FT6 = 0 | 54 | Not a fit |
| Subros vs an SME competing with Denso | Denso holds 20% -> FT6 = 0 | 71 | Not a fit (`subros_fit_denso_rival.json`) |

The last row is the deck's example: the same Trust Score, but Fit changes with each SME.
