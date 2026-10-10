# Medlivo AI Platform — Phase 1 Margin & Cost Engine Specification

**Status:** FINALIZED Phase 1 business specification  
**Purpose:** Convert the approved Medlivo GM calculators and prior product decisions into one enterprise Margin & Cost Engine that can be used by recruiters, Delivery Managers, Executives, and developers without relying on spreadsheet math.

## 1. Governing principle

The platform must not embed three unrelated spreadsheet calculators.

The uploaded workbooks are the authoritative formula-validation and current-assumption references for the initial calculation profiles:

1. **Nursing & Allied — California W-2**
   - Source workbook: `Anand - Medlivo Recruiter GM Calculator.xlsx`
   - Source sheets: California GM Calculator, CA Engine, Internal Calculations, Rules & Calculations

2. **Nursing & Allied — National W-2**
   - Source workbook: `Anand - Medlivo Recruiter GM Calculator.xlsx`
   - Source sheets: National GM Calculator, National Engine, Internal Calculations, Rules & Calculations

3. **Rehabilitation — California W-2**
   - Source workbook: `Prachi Medlivo Recruiter GM Calculator.xlsx`
   - Source sheets: California GM Calculator, CA Engine, Internal Calculations, Rules & Calculations

4. **Rehabilitation — National W-2**
   - Source workbook: `Prachi Medlivo Recruiter GM Calculator.xlsx`
   - Source sheets: National GM Calculator, National Engine, Internal Calculations, Rules & Calculations

5. **Locum Tenens — California W-2**
   - Source workbook: `Medlivo CA Locums W-2 GM Calculator.xlsx`
   - Source sheets: CA Locums W-2 GM Calculator, CA Locums Engine, Pricing Summary, Admin Assumptions

6. **Locum Tenens — Nationwide 1099**
   - Source workbook: `Medlivo Locums 1099 GM Calculator.xlsx`
   - Source sheets: 1099 GM Calculator, Locums Engine, Pricing Summary, Rules

The platform must reproduce tested business rules in code and keep assumptions versioned. It must not copy spreadsheet layout as the application architecture.

---

## 2. Placement in Medlivo architecture

**Owning domain:** Margin & Economics  
**Primary workflow service:** Team Workspace  
**Consumers:** Recruiter Workspace, Delivery Manager Workspace, Executive Command Center

JobDiva remains the ATS system of record for jobs, candidates, submissions, placements, and ATS workflow status.

QuickBooks remains the accounting system for actual invoicing, A/R, collections, accounting, and financial statements.

Medlivo AI owns:
- projected economics
- pay-package calculations
- versioned assumptions
- margin snapshots
- margin guideline evaluation and exception discussions
- projected commission
- negotiation history
- audit trail

---

## 3. Recruiter workflow

The engine is embedded in the job/candidate negotiation workflow.

`Job economics → recruiter negotiates compensation → live recalculation → guideline check → recruiter finalizes within guideline → discussion with Delivery Manager or designated leadership when needed → immutable economics snapshot`

Recruiters must not manually calculate GM.

Recruiters may edit only authorized negotiable fields, such as:
- taxable pay / contractor pay
- stipends where allowed
- bonuses
- callback / standby / orientation compensation where applicable
- travel or assignment reimbursements where authorized

Recruiters may not edit:
- payroll burden
- workers' compensation assumptions
- insurance assumptions
- factoring assumptions
- overhead assumptions
- customer/MSP fee rules
- guideline thresholds
- commission rules
- protected company cost assumptions

---

## 4. Core calculation model

### Revenue

**Gross Client Billing** includes all applicable billable components:
- scheduled work
- overtime / double-time billing where applicable
- callback
- standby / call
- orientation
- other approved billable components

**MSP/VMS Fee**

For MSP/VMS customers:

`MSP/VMS Fee = Gross Client Billing × Effective MSP/VMS Fee %`

For Direct Customers:

`MSP/VMS Fee = 0`

**Net Client Billing**

`Net Client Billing = Gross Client Billing - MSP/VMS Fee`

### Cost

Total projected assignment cost may include, depending on calculation profile:
- wages or contractor compensation
- California OT / DT premium
- payroll taxes
- workers' compensation
- paid sick leave reserve
- employer medical / dental / vision contribution
- housing / hotel
- meals & incidentals
- rental car
- mileage reimbursement
- other weekly non-taxable assignment costs
- professional liability / malpractice
- factoring
- internal overhead
- credentialing / onboarding
- sourcing cost
- orientation cost
- airfare
- license
- DEA
- sign-on bonus
- completion bonus
- assignment stipend
- other approved one-time costs

### Gross Margin

`Gross Margin = Net Client Billing - Total Projected Cost`

### Gross Margin Percentage

**Finalized rule:**

`GM % = Gross Margin ÷ Net Client Billing`

GM % must not be calculated against gross billing.

---

## 5. Calculation profiles

## 5.1 Nursing & Allied — California W-2

Current workbook assumptions used as initial seed values:

| Assumption | Initial workbook value |
| --- | ---: |
| Employer payroll taxes | 10.6% of taxable wages |
| Workers' compensation | 3.4% of taxable wages |
| Professional liability & other insurance | 2.5% of net billing |
| Factoring fee | 2.4% of net billing |
| Internal overhead | 3.5% of net billing |
| Default MSP/VMS fee | 6.0% of gross billing |
| Default required minimum taxable rate | $24/hour |
| Default contract length | 13 weeks |
| Nursing/Allied onboarding | $850 per new contract |
| Rehab onboarding | $500 per new contract |
| Vivian sourcing cost | $1,400 per new contract |
| Medical premium | $400/month |
| Dental premium | $75/month |
| Vision premium | $20/month |
| Employer contribution | 50% |
| Paid sick leave reserve | 1 hour per 30 hours worked |
| OT multiplier | 1.5x |
| Double-time multiplier | 2.0x |

California OT/DT must remain automatic and conservative.

The current workbook determines daily and weekly overtime and double-time from shift length, shifts/week, scheduled hours, expected OT, callback, holiday, and other paid components.

The recruiter must not choose whether California OT/DT applies.

## 5.2 Nursing & Allied — National W-2

Initial workbook assumptions are the same as California except:

| Assumption | Initial workbook value |
| --- | ---: |
| Workers' compensation | 1.5% of taxable wages |
| California taxable floor | Not applicable |

National profile supports configurable weekly OT treatment, including the current workbook's standard OT logic and approved exceptions such as the represented 48-Regular/No-OT rule.

These rules must be configuration/policy driven rather than recruiter-entered free text in production.

## 5.3 Rehabilitation — California W-2

Authoritative source: `Prachi Medlivo Recruiter GM Calculator.xlsx`.

The current protected assumptions and formula structure match the corresponding Nursing & Allied California rules, but Rehabilitation remains a **separate calculation profile** so future Rehab policy changes cannot affect Nursing & Allied.

Initial workbook assumptions:
- Employer payroll taxes: 10.6% of taxable wages
- Workers' compensation: 3.4% of taxable wages
- Professional liability & other insurance: 2.5% of net billing
- Factoring: 2.4% of net billing
- Internal overhead: 3.5% of net billing
- Default MSP/VMS fee: 6.0% of gross billing
- Rehab credentialing/onboarding: $500 per New Contract
- Vivian sourcing: $1,400 per New Contract
- W-2 benefits and sick-leave reserve use the approved protected assumptions
- California OT and double-time remain automatic and conservative

## 5.4 Rehabilitation — National W-2

Authoritative source: `Prachi Medlivo Recruiter GM Calculator.xlsx`.

The current protected assumptions and formula structure match the corresponding Nursing & Allied National rules, but Rehabilitation remains a **separate calculation profile**.

Initial workbook assumptions:
- Employer payroll taxes: 10.6% of taxable wages
- Workers' compensation: 1.5% of taxable wages
- Professional liability & other insurance: 2.5% of net billing
- Factoring: 2.4% of net billing
- Internal overhead: 3.5% of net billing
- Default MSP/VMS fee: 6.0% of gross billing
- Rehab credentialing/onboarding: $500 per New Contract
- Vivian sourcing: $1,400 per New Contract
- National OT policy remains configuration driven

## 5.5 Locum Tenens — California W-2

Current workbook assumptions used as initial seed values:

| Assumption | Initial workbook value |
| --- | ---: |
| Employer payroll taxes | 10.6% of taxable wages |
| California workers' compensation | 3.4% of taxable wages |
| Professional liability & other insurance | 2.5% of net billing |
| Factoring fee | 2.4% of net billing |
| Internal overhead | 3.5% of net billing |
| Default MSP/VMS fee | 6.0% of gross billing |
| Minimum hourly pricing check | $24/hour |
| Credentialing / onboarding | $1,200 per clinician |
| Vivian sourcing cost | $1,400 per placement |
| Referral sourcing cost | $500 per placement |
| Medical premium | $400/month |
| Dental premium | $75/month |
| Vision premium | $20/month |
| Employer contribution | 50% |
| Paid sick leave reserve | 1 hour per 30 hours worked |
| OT multiplier | 1.5x |
| Double-time multiplier | 2.0x |

The workbook also contains a 2026 physician hourly threshold reference. That reference must remain an administrative policy input and must not allow recruiters to bypass the conservative California W-2 OT/DT calculation.

Supported economics include:
- hourly / flat client rate structures
- provider W-2 compensation
- scheduled shifts
- callback
- standby/on-call
- orientation
- housing / hotel
- M&I
- rental car
- mileage
- licensing / DEA
- bonuses
- one-time assignment costs

## 5.6 Locum Tenens — Nationwide 1099

Current workbook assumptions used as initial seed values:

| Assumption | Initial workbook value |
| --- | ---: |
| Workers' compensation reserve | 3.4% of contractor compensation |
| Professional liability / malpractice | 2.5% of net billing |
| Factoring fee | 2.4% of net billing |
| Internal overhead | 3.5% of net billing |
| Default MSP/VMS fee | 6.0% of gross billing |
| Credentialing / onboarding | $1,200 per provider |
| Vivian sourcing cost | $1,400 per placement |
| Referral sourcing cost | $500 per placement |
| Workbook approval threshold | 10.0% GM |

Supported assignment types:
- Per Diem
- Contract
- Travel Contract

Supported rate structures:
- Hourly
- Per Shift
- Daily
- 24-Hour Call

The engine must calculate:
- planned/total shifts
- assignment-week equivalent
- scheduled hours
- bill per shift
- contractor pay per shift
- callback billing/pay
- standby billing/pay
- orientation billing/pay
- bonuses
- travel costs
- one-time costs
- per-shift economics
- per-week economics
- full-assignment economics

---

## 6. Rate finalization and guideline policy

Recruiters own rate negotiation and rate finalization. They are expected to follow Medlivo's approved commercial guidelines and do not require routine manager approval for normal rate decisions.

Guideline thresholds must be **versioned configuration**, not hardcoded application logic.

The uploaded spreadsheets contain historical/current reference thresholds:
- California Locums W-2 workbook: 5% historical approval/reference threshold
- Locums 1099 workbook: 10% historical approval/reference threshold

These workbook values are inputs to the guideline configuration. They are not a universal enterprise approval rule.

The Nursing/Allied/Rehab workbook does not establish one universal enterprise threshold in its protected assumptions table.

The platform must support configurable guideline bands by:
- calculation profile
- division
- customer/MSP where needed
- effective date

Final workflow:

### Within guideline
Recruiter may finalize the negotiated rate directly.

### Discuss with Delivery Manager
The package falls outside the normal recruiter guideline or contains an unusual commercial consideration. The platform flags the item for discussion, but the recruiter remains the primary rate owner.

### Discuss with leadership
The economics are materially outside normal guidance or involve a significant exception. The recruiter discusses with the Delivery Manager and/or designated leadership. Lael may serve as a designated leadership contact operationally, but the software must use role/configuration rather than hardcoding an individual's name.

### Negative GM
Negative GM cannot be treated as an ordinary recruiter-finalized package. It requires an explicit leadership exception before the platform may treat the package as final.

The UI should display plain-language status:
- Within Guideline
- Discuss with Delivery Manager
- Discuss with Leadership
- Negative GM — Leadership Exception Required
- Guideline Not Configured

The platform must preserve which guideline-policy version was applied and whether a discussion/exception was recorded.

---

## 7. Versioned assumptions

Create a versioned `CostAssumptionSet`.

Minimum fields:
- assumption_set_id
- calculation_profile
- version
- effective_from
- effective_to
- payroll_tax_rate
- workers_comp_rate
- sick_leave_reserve_rule
- professional_liability_rate
- factoring_rate
- overhead_rate
- default_msp_fee
- onboarding_cost
- sourcing_cost_by_source
- benefit premiums
- employer benefit contribution
- minimum taxable / pricing check
- OT multiplier
- DT multiplier
- guideline bands
- commission rule
- approved_by
- created_at

Historical margin snapshots must always reference the assumption-set version used at calculation time.

Changing an assumption must never rewrite historical deal economics.

---

## 8. Customer / MSP overrides

Default assumptions may be overridden by approved customer-specific terms.

Examples:
- MSP/VMS fee
- rate card
- orientation billing policy
- guaranteed-hours rules
- reimbursement treatment
- customer-specific insurance cost allocation
- other contractual economics

Priority:

`Approved Customer/MSP Rule → Calculation Profile Rule → Company Default`

Every override must be effective-dated and auditable.

---

## 9. Candidate sourcing cost

Initial workbook logic includes:
- Internal Database: $0
- Vivian: $1,400
- Referral: $500 where represented by Locums
- future approved sources may have configured acquisition cost

Sourcing cost is applied by rule, not typed manually by recruiters unless an authorized exception workflow permits it.

---

## 10. Benefits

For W-2 profiles, employer benefits are calculated only when applicable.

Current seed assumptions:
- Medical: $400/month
- Dental: $75/month
- Vision: $20/month
- Employer contribution: 50%

Weekly employer benefit cost should use the approved monthly-to-weekly conversion rule.

Benefit assumptions remain versioned.

---

## 11. One-time and recurring costs

The engine must classify every cost as one of:

### Recurring
Examples:
- weekly wages
- weekly stipends
- payroll burden
- weekly housing
- M&I
- rental car
- mileage
- recurring insurance/overhead/factoring allocation

### One-time
Examples:
- credentialing/onboarding
- sourcing
- airfare
- state license
- DEA
- sign-on bonus
- completion bonus
- assignment stipend
- other approved one-time cost

One-time costs must be:
- shown separately
- included in full-assignment profit
- allocated into weekly/per-hour views only for presentation where needed

The underlying assignment-level amount must remain preserved.

---

## 12. Negotiation snapshots

Every meaningful recruiter negotiation change creates an immutable `MarginCalculationSnapshot`.

Required fields:
- snapshot_id
- job_id
- candidate_id
- recruiter_user_id
- calculation_profile
- assumption_set_id
- customer rule version
- version number
- bill-rate inputs
- pay-package inputs
- schedule inputs
- cost components
- net billing
- total projected cost
- GM $
- GM %
- projected assignment profit
- commissionable net profit basis
- projected recruiter commission
- guideline status
- created_by
- created_at
- finalized_at

States:
- Draft
- Negotiated
- Discussion Recommended
- Leadership Exception Required
- Finalized
- Superseded

Never overwrite a prior negotiation version.

---

## 13. Recruiter commission

Finalized business rule from prior product decisions:

`Projected Recruiter Commission = 3% × Commissionable Net Profit`

The platform must have one authoritative field:

**Commissionable Net Profit**

Keep separate:
- Projected Commission
- Approved / Earned Commission

A projected calculator result must never become payroll/accounting truth automatically.

---

## 14. Projected vs actual economics

### Projected economics
Owned by Medlivo AI Margin Engine:
- projected billing
- projected cost
- projected GM
- projected GM %
- projected assignment profit
- projected commission

### Actual economics
Derived later from authoritative operating/accounting sources:
- actual worked hours
- actual billing
- actual payroll/provider cost
- actual reimbursed costs
- actual profit
- approved earned commission

QuickBooks remains the accounting system.

Phase 1 must design the data model so projected and actual values are never mixed, even if actual-profit ingestion is implemented later.

---

## 15. Required validations

The engine must fail closed or require review for materially incomplete economics.

Examples:
- bill rate missing
- pay rate missing
- schedule/shift basis missing
- assignment length missing when required
- callback selected without bill/pay rates
- standby selected without units/rates
- orientation selected without pay treatment
- W-2 taxable rate below configured pricing floor
- California OT/DT billing inputs requiring verification
- negative GM
- invalid customer/MSP fee
- missing assumption-set version

A job may be **Recruiting Ready** while bill rate is unknown, but the pay package cannot be finalized as Commercially Ready until an approved commercial basis exists.

---

## 16. Role authority

### Recruiter
Can:
- enter/adjust negotiable compensation
- view live economics
- save negotiation versions
- finalize rates within approved guidelines
- request or record discussion when the system flags an exception

Cannot:
- modify protected company assumptions
- change customer fee rules
- modify protected guideline policy
- bypass a required negative-GM leadership exception

### Delivery Manager
Can:
- view all assumptions affecting a deal
- discuss margin exceptions with recruiters
- provide guidance on out-of-guideline packages
- correct permitted commercial data
- see projected commission impact

Cannot:
- change master company assumptions unless separately granted System Admin authority

### Executive / Designated Leadership
Can:
- record leadership exceptions when required
- view profitability summaries
- authorize assumption/policy changes where required

### System Admin / Authorized Finance
Can:
- maintain versioned assumption sets
- configure guideline bands
- configure customer/MSP economics
- maintain sourcing/benefit/cost rules

All changes are audited.

---

## 17. User experience requirements

The recruiter should not be shown a finance spreadsheet.

The workflow should show:

### Inputs recruiter controls
Only the fields relevant to the negotiation.

### Live impact
- current package
- proposed package
- change in GM %
- change in projected assignment profit
- projected commission impact

### Guardrail
Plain language:
- Healthy
- Discuss with Delivery Manager
- Discuss with Leadership
- Negative GM — Leadership Exception Required

### Explanation
The recruiter/manager can open **Why?** to see:
- MSP/VMS fee
- payroll burden
- workers' comp
- insurance
- factoring
- overhead
- onboarding/sourcing
- travel/one-time costs
- applicable OT/DT impact

No manual margin math should be necessary.

---

## 18. Phase 1 implementation entities

Minimum implementation:

### `cost_assumption_set`
Versioned protected assumptions.

### `customer_economic_rule`
Customer/MSP-specific overrides.

### `margin_calculation_snapshot`
Immutable calculation result and inputs.

### `margin_cost_component`
Detailed normalized cost breakdown.

### `margin_discussion` / exceptional `approval_request`
Normal rate finalization does not create an approval request. Record recruiter/Delivery Manager/leadership discussions when guidance is needed. Use the generic approval domain only for true hard exceptions such as an explicitly governed negative-GM leadership exception.

### `commission_projection`
Projected commission tied to finalized snapshot.

### `margin_audit_event`
Use the platform operational audit domain.

---

## 19. Formula validation requirement

Before production release, the coded engine must be regression-tested against the uploaded calculators.

Create test fixtures covering at minimum:

- California Nursing RN
- California Rehab PT
- National Nursing RN
- National Rehab PT
- California Locums W-2 hourly
- California Locums W-2 with callback
- California Locums W-2 with standby
- California Locums W-2 with orientation
- Locums 1099 Per Diem
- Locums 1099 Contract
- Locums 1099 Travel Contract
- direct customer fee = 0
- MSP/VMS fee override
- Vivian sourcing
- referral sourcing where applicable
- benefits on/off
- extension with onboarding/sourcing suppression where workbook rules require
- negative GM
- Delivery Manager discussion band
- leadership discussion band

For every fixture, platform outputs must reconcile to the authoritative workbook within an explicitly defined currency/percentage rounding tolerance.

---

## 20. Locked Phase 1 decisions

The following are finalized:

- One enterprise Margin & Cost Engine, not separate spreadsheet codebases
- Six initial calculation profiles: Nursing & Allied CA/National, Rehabilitation CA/National, Locums CA W-2, and Locums Nationwide 1099
- GM % uses Net Client Billing
- recruiter never manually calculates GM
- cost assumptions are versioned
- customer/MSP rules can override defaults
- negotiation snapshots are immutable/versioned
- Delivery Manager has high visibility and provides guidance on flagged exceptions; recruiters remain the primary rate decision-makers
- master assumptions remain protected
- rate guideline thresholds are configurable/versioned, not globally hardcoded
- negative GM is a hard exception
- bill rate must not be invented
- projected and actual economics remain separate
- QuickBooks is not duplicated
- recruiter commission is 3% of Commissionable Net Profit
- public/recruiting workflows cannot bypass margin guideline and hard-exception rules
- uploaded calculators remain formula-validation references for the initial engine implementation

This specification is the governing business definition for the Phase 1 Margin & Cost Engine.
