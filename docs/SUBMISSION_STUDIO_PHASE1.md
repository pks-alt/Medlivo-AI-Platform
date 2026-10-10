# Phase 1 Submission Studio

## Purpose

Medlivo Submission Studio reduces recruiter submission preparation from a manual 1–2 hour process to an AI-assisted review workflow. It does not copy legacy customer packets. It uses them only to learn the kinds of information, evidence, forms, and ordering rules that customer/MSP programs may require.

The target recruiter experience is:
1. choose or open the matched candidate/job,
2. Medlivo automatically selects the correct customer/program template,
3. AI assembles and validates the package,
4. recruiter reviews only exceptions and editable narrative,
5. recruiter previews and downloads the final package,
6. recruiter submits through the customer's current channel until controlled write-back/automation is authorized.

## Division model

### Rehabilitation
Rehab supports:
- Medlivo Rehab default
- direct-customer template family
- MSP/VMS template family
- customer/program/profession/job overrides

### Nursing & Allied
Nursing & Allied is MSP/VMS-only for Phase 1.
There is no direct-customer template branch.

Template precedence:
1. Job override
2. MSP/VMS program + profession/specialty
3. MSP/VMS program
4. MSP/VMS customer
5. Nursing & Allied division default
6. Medlivo default

Examples that informed the architecture:
- Kaiser-style programs may require candidate security data, program-specific checklists, nursing education, work-history/gap attestations, vaccination answers, specialty skills, and derived identifiers.
- Medical Solutions-style programs may require resume, licensure/certification data, EMR/background attestations, specialty skills, references, primary-source verification, and selected supporting documents.

These are examples, not hard-coded universal rules.



### Locum Tenens
Locum Tenens is MSP/VMS-only for Phase 1.
There is no direct-customer template branch.

Template precedence:
1. Job override
2. MSP/VMS program + provider type/specialty
3. MSP/VMS program
4. MSP/VMS customer
5. Locum Tenens division default
6. Medlivo default

Locums submission is document-heavy and generally treated as a full credential presentation. Customer/program templates may require most or all of the following at submission:
- CV/resume with required gap explanations
- active state license verification
- board certification verification
- DEA registration
- NPI
- BLS / ACLS / specialty certifications
- malpractice disclosure/attestation
- criminal/background or sex-offender search evidence where required
- vaccination/exemption evidence where required
- availability, shift/call coverage and requested time off
- recent clinical activity / date last worked
- EMR experience
- procedures and case/procedure experience relevant to the job
- provider highlights
- customer presentation form
- rates, admin fees, travel/lodging terms where the customer presentation requires them

The package engine must distinguish a credential card/copy from official primary-source verification. A board-certification card may demonstrate a credential while still requiring separate official verification. Templates can therefore require both a credential copy and a primary-source verification as separate requirements.

DEA registrations are jurisdiction-sensitive. The engine must preserve registration number, expiration, registered business activity, state/location restrictions, and the evidence source. It must never assume that one DEA registration satisfies a different state/program requirement.

For locums, submission composition should connect to the finalized Pay Package/GM snapshot when commercial fields are required. Recruiters should not retype bill rate, OT rate, admin fee, travel or lodging terms that already exist in governed Medlivo economics.

The AI CV composer must detect and remove non-resume commentary or drafting artifacts before generating the submission CV. AI may improve structure and relevance but may not invent gap explanations, procedures, case volume, certifications, licenses, malpractice history, or availability.


## Requirement lifecycle

Every template requirement has a lifecycle stage:
- submission
- credentialing
- start

This prevents recruiters from collecting everything at submission time when a document is only needed later.

A customer/program template may promote a normally-later item into the submission stage when explicitly required.

## Requirement sensitivity

Every requirement is classified:
- standard
- internal
- confidential
- restricted

Restricted examples include partial SSN, date of birth elements, government IDs, and similarly sensitive identifiers.

Rules:
- restricted data is never included merely because it exists,
- it is rendered only when an active template explicitly requires it,
- outputs should use the minimum required representation,
- AI cannot infer or invent restricted values,
- derived identifiers may be generated only from confirmed source values using a deterministic rule,
- access and generation events must be auditable.

## Fulfillment strategy

Requirements use one of four strategies:
- source_only: must come from trusted source data/document evidence
- source_or_ai: AI may normalize/summarize source-supported facts
- derived: deterministic computation from confirmed source values
- manual_confirmation: recruiter/candidate must explicitly confirm

Examples:
- license expiration: source_only
- candidate presentation summary: source_or_ai
- customer security ID: derived
- requested time off confirmation: manual_confirmation or source_only if already confirmed

## Candidate Knowledge Layer

Submission Studio reuses a normalized candidate knowledge layer instead of re-reading every document for every submission.

Reusable facts include:
- profession/specialty
- settings
- work history and gaps
- education
- licenses and compact status
- certifications and expiration dates
- EMR experience
- skills-checklist metadata
- references
- availability
- requested time off
- assignment preferences

Every fact must preserve provenance.

## Candidate Document Wallet

Reusable candidate document assets include:
- source resume
- Medlivo canonical resume
- state licenses
- primary-source license verification
- certifications
- skills checklists
- professional references
- customer/application forms
- immunization evidence when required
- identity documentation when required
- other customer-specific artifacts

Each document asset stores:
- document type
- source
- verification state
- issue/expiration dates where applicable
- extracted facts
- current/stale state
- content hash
- AI classification metadata

## AI Resume Composer

The resume engine may:
- normalize structure and formatting,
- emphasize source-supported experience relevant to the job,
- standardize dates and role naming,
- summarize clinical settings and specialty exposure,
- remove unnecessary personal/contact information when customer rules require,
- generate a consistent Medlivo visual format,
- generate customer-specific variants when required.

It may not:
- invent experience,
- create unsupported skills,
- alter employment dates without evidence,
- claim credentials that cannot be verified,
- silently resolve factual conflicts.

## AI Candidate Presentation

The candidate summary should be concise and job-specific.

Preferred structure:
- current profession/specialty
- directly relevant experience
- clinical settings
- active license/credential status
- availability/start alignment
- key customer-fit factors

Avoid generic filler such as "enthusiastic candidate" unless supported and useful.

## Validation Engine

Validation runs before recruiter review.

Blocking examples:
- required document missing
- required license not active
- required skills checklist absent/stale
- required customer form incomplete
- unresolved conflicting license number/expiration
- required attestation missing
- required security identifier cannot be generated from confirmed inputs

Warning examples:
- credential near expiration
- resume employment date conflict
- unexplained gap under customer rules
- specialty checklist older than customer threshold
- reference older than customer threshold

AI-detected conflicts must show evidence and recommended resolution, but not silently overwrite verified data.

## Submission Readiness

Statuses:
- not_started
- missing_required
- needs_review
- ready

Readiness is deterministic.

AI may explain why the package is not ready, but cannot mark a package ready when blocking requirements remain unresolved.

Suggested recruiter-facing metrics:
- percent complete
- required items satisfied
- open blocking issues
- open review items
- reusable documents matched
- AI-filled fields
- recruiter confirmations needed

## Package Output

A template may request:
- one combined PDF,
- separate named documents,
- both combined and separate outputs,
- a customer-specific order,
- a customer-specific naming convention.

Generated outputs should be versioned and tied to:
- template ID/version
- candidate/job
- package version
- generation timestamp
- validation state
- recruiter who finalized

## Nursing & Allied program considerations

Because all Nursing & Allied customers are MSP/VMS in Phase 1, the product should optimize for program variation rather than direct-customer variation.

Examples of supported program rules:
- candidate checklist required
- nursing education required
- minimum recent-experience window
- employment-gap explanation threshold
- facility prior-employment disclosure
- specialty skills checklist and age threshold
- EMR requirement
- license verification requirement
- license compact-state logic
- vaccination attestation
- references at submission vs credentialing
- security-ID derivation
- state-specific or client-specific license requirement
- specialty certifications

## Human review

Recruiters should review:
- AI-created narrative
- conflicts
- missing/uncertain items
- manual attestations
- restricted data before it is included
- final preview

They should not have to manually reassemble known facts and previously verified documents for each submission.

## Phase 2

Phase 2 can add:
- candidate self-service requests for missing items
- automated form completion
- controlled e-signature workflows
- automated follow-up for expiring/missing documents
- customer/VMS write-back where technically and contractually allowed
- conversion learning by customer/template
- AI recommendations based on historical submission outcomes

Phase 1 must establish the correct template, provenance, validation, privacy, artifact, and review architecture first.
