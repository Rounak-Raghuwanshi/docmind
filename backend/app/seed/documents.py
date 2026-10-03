"""Demo document content.

Two workspaces: Indian tax and GST study notes (the public demo), and an engineering handbook
that shows how a tech team can use DocMind. The figures are illustrative summaries of
FY 2025-26 provisions written for the demo. They are not legal advice.
"""

from dataclasses import dataclass, field

DISCLAIMER = (
    "Illustrative study notes prepared for the DocMind demo. Figures summarise FY 2025-26 "
    "(AY 2026-27) provisions as commonly published. Always verify against the official Act, "
    "rules and the latest CBDT / CBIC notifications before relying on them."
)


@dataclass
class Section:
    heading: str
    paragraphs: list[str]
    bullets: list[str] = field(default_factory=list)


@dataclass
class DemoDoc:
    filename: str
    title: str
    kind: str  # "pdf" | "docx" | "md"
    sections: list[Section]
    summary: str
    questions: list[str]
    scanned: bool = False  # render as images so ingestion has to OCR it


TAX_DOCS: list[DemoDoc] = [
    DemoDoc(
        filename="Income-Tax-Deductions-Guide-FY2025-26.pdf",
        title="Income Tax Deductions Guide, FY 2025-26",
        kind="pdf",
        summary=(
            "A guide to the deductions and exemptions individual taxpayers use most: Section 80C, "
            "80D, 80CCD(1B), 80E, 80TTA/80TTB, 80G and HRA. It compares the old and new tax "
            "regimes, including the Section 87A rebate that makes income up to ₹12 lakh tax-free "
            "under the new regime."
        ),
        questions=[
            "How much can I claim under Section 80D for my parents?",
            "Is income up to 12 lakh tax-free in the new regime?",
            "How is HRA exemption calculated?",
        ],
        sections=[
            Section(
                "About these notes",
                [DISCLAIMER],
            ),
            Section(
                "Chapter 1: Old regime vs new regime",
                [
                    "Every resident individual chooses between two ways of computing income tax. "
                    "The new tax regime under Section 115BAC is the default from FY 2023-24 onwards. "
                    "It offers lower slab rates but removes most deductions and exemptions. The old "
                    "regime keeps the familiar deductions such as Section 80C, 80D and the HRA "
                    "exemption, but its slab rates are higher.",
                    "New regime slab rates for FY 2025-26 are: income up to ₹4 lakh is nil; ₹4 to 8 "
                    "lakh is taxed at 5%; ₹8 to 12 lakh at 10%; ₹12 to 16 lakh at 15%; ₹16 to 20 lakh "
                    "at 20%; ₹20 to 24 lakh at 25%; and income above ₹24 lakh at 30%. Health and "
                    "education cess of 4% is added to the tax.",
                    "Old regime slab rates for individuals below 60 years are: up to ₹2.5 lakh nil; "
                    "₹2.5 to 5 lakh at 5%; ₹5 to 10 lakh at 20%; and above ₹10 lakh at 30%.",
                    "Salaried employees should compare both regimes every year. A taxpayer with large "
                    "deductions, for example a home loan, full 80C investments and high rent, may "
                    "still pay less under the old regime.",
                ],
            ),
            Section(
                "Chapter 2: Section 87A rebate and standard deduction",
                [
                    "Under the new regime for FY 2025-26, a resident individual whose taxable income "
                    "does not exceed ₹12 lakh gets a rebate under Section 87A of up to ₹60,000. In "
                    "practice this makes income up to ₹12 lakh tax-free. Marginal relief applies to "
                    "income slightly above ₹12 lakh, so tax never exceeds the income above that limit.",
                    "Salaried individuals also receive a standard deduction of ₹75,000 under the new "
                    "regime (₹50,000 under the old regime). Together with the rebate, a salary of up "
                    "to ₹12.75 lakh can be tax-free under the new regime.",
                    "The rebate does not apply to income taxed at special rates, such as long-term "
                    "capital gains under Section 112A. Under the old regime the Section 87A rebate is "
                    "up to ₹12,500 for taxable income up to ₹5 lakh.",
                ],
            ),
            Section(
                "Chapter 3: Section 80C investments",
                [
                    "Section 80C allows a deduction of up to ₹1,50,000 in a financial year for "
                    "specified investments and payments. It is available only under the old regime.",
                ],
                bullets=[
                    "Public Provident Fund (PPF) and Employees' Provident Fund (employee contribution)",
                    "Equity Linked Savings Schemes (ELSS), which have a three-year lock-in, the shortest among 80C options",
                    "Life insurance premiums for self, spouse and children",
                    "Tuition fees for up to two children at an Indian school or college",
                    "Principal repayment of a home loan, and stamp duty paid on the purchase",
                    "National Savings Certificate, 5-year tax-saver bank deposits, Sukanya Samriddhi Yojana",
                ],
            ),
            Section(
                "Chapter 4: Section 80D health insurance",
                [
                    "Section 80D gives a deduction for health insurance premiums. For self, spouse "
                    "and dependent children the limit is ₹25,000, or ₹50,000 if the taxpayer or spouse "
                    "is a senior citizen (60 years or more).",
                    "Premiums paid for parents qualify for an additional deduction of ₹25,000, rising "
                    "to ₹50,000 when the parents are senior citizens. A taxpayer who is a senior citizen "
                    "and pays for senior citizen parents can therefore claim up to ₹1,00,000 in total.",
                    "Preventive health check-ups qualify for up to ₹5,000. This amount is within the "
                    "overall 80D limits, not in addition to them. Premiums must be paid by any mode "
                    "other than cash; only the preventive check-up may be paid in cash.",
                ],
            ),
            Section(
                "Chapter 5: NPS, education loans, savings interest and donations",
                [
                    "Section 80CCD(1B) allows an extra deduction of up to ₹50,000 for contributions to "
                    "the National Pension System, over and above the ₹1.5 lakh limit of Section 80C. "
                    "The employer's contribution under Section 80CCD(2) is deductible under both "
                    "regimes, up to 14% of salary in the new regime.",
                    "Section 80E allows the full interest paid on a loan for higher education, with no "
                    "upper limit, for up to eight years from the year repayment starts. The loan must "
                    "be from a bank or an approved charitable institution.",
                    "Section 80TTA allows up to ₹10,000 of savings account interest to be deducted by "
                    "individuals below 60. Senior citizens instead use Section 80TTB, which covers up to "
                    "₹50,000 of interest on savings and fixed deposits.",
                    "Section 80G gives a deduction of 50% or 100% of donations to approved funds and "
                    "charities, some subject to a qualifying limit of 10% of adjusted gross total "
                    "income. Cash donations above ₹2,000 are not eligible.",
                ],
            ),
            Section(
                "Chapter 6: House Rent Allowance (HRA)",
                [
                    "Salaried employees who live in rented accommodation can claim an exemption for HRA "
                    "under Section 10(13A), available only in the old regime. The exempt amount is the "
                    "least of three figures: the actual HRA received; rent paid minus 10% of salary; "
                    "and 50% of salary for Mumbai, Delhi, Kolkata or Chennai, or 40% of salary in "
                    "other cities. Salary here means basic pay plus dearness allowance.",
                    "If annual rent exceeds ₹1 lakh, the employee must give the landlord's PAN to the "
                    "employer. Paying rent to a parent is allowed if the parent owns the property and "
                    "declares the rent as income.",
                ],
            ),
        ],
    ),
    DemoDoc(
        filename="Capital-Gains-and-Advance-Tax.pdf",
        title="Capital Gains and Advance Tax",
        kind="pdf",
        summary=(
            "How gains on shares, mutual funds and property are taxed after the July 2024 changes "
            "(20% STCG, 12.5% LTCG with a ₹1.25 lakh exemption), holding periods, and the advance "
            "tax schedule with interest under Sections 234B and 234C."
        ),
        questions=[
            "What is the tax on long-term capital gains from listed shares?",
            "When are advance tax installments due?",
            "How are debt mutual funds taxed?",
        ],
        sections=[
            Section("About these notes", [DISCLAIMER]),
            Section(
                "Part A: Short-term and long-term capital gains",
                [
                    "A gain is short-term or long-term depending on how long the asset was held. "
                    "Listed shares, equity mutual funds and listed securities are long-term when held "
                    "for more than 12 months. Most other assets, including property and unlisted "
                    "shares, are long-term after 24 months.",
                    "For transfers on or after 23 July 2024, short-term capital gains on listed equity "
                    "shares and equity-oriented mutual funds (where securities transaction tax is paid) "
                    "are taxed at 20% under Section 111A.",
                    "Long-term capital gains on listed equity shares and equity mutual funds are taxed "
                    "at 12.5% under Section 112A. The first ₹1.25 lakh of such gains in a financial "
                    "year is exempt.",
                    "Long-term gains on other assets are taxed at 12.5% without indexation. For land "
                    "or buildings acquired before 23 July 2024, resident individuals and HUFs may "
                    "instead compute tax at 20% with indexation, whichever is lower.",
                    "Gains on debt mutual funds purchased on or after 1 April 2023 are always treated "
                    "as short-term under Section 50AA and taxed at the investor's slab rate.",
                ],
            ),
            Section(
                "Part B: Exemptions for reinvestment",
                [
                    "Section 54 exempts long-term gains from selling a residential house when the gain "
                    "is reinvested in another residential house within the prescribed time, subject to "
                    "a cap of ₹10 crore. Section 54EC exempts gains of up to ₹50 lakh invested in "
                    "specified bonds within six months, with a five-year lock-in.",
                ],
            ),
            Section(
                "Part C: Advance tax",
                [
                    "Advance tax is income tax paid during the year instead of in one go at year end. "
                    "It applies when the estimated tax liability for the year, after TDS, is ₹10,000 "
                    "or more. Resident senior citizens without business or professional income are "
                    "exempt.",
                ],
                bullets=[
                    "By 15 June: at least 15% of the estimated tax",
                    "By 15 September: at least 45%",
                    "By 15 December: at least 75%",
                    "By 15 March: 100% of the estimated tax",
                ],
            ),
            Section(
                "Part D: Interest for late or short payment",
                [
                    "Taxpayers under the presumptive schemes of Section 44AD or 44ADA may pay the full "
                    "advance tax in one installment by 15 March.",
                    "Section 234B charges simple interest of 1% per month when advance tax paid is "
                    "less than 90% of the assessed tax. Section 234C charges 1% per month for deferring "
                    "individual installments. Both are computed automatically while filing the return.",
                ],
            ),
        ],
    ),
    DemoDoc(
        filename="GST-Registration-and-Returns.pdf",
        title="GST Registration, Returns and Input Tax Credit",
        kind="pdf",
        summary=(
            "Who must register for GST and when, the composition scheme, GSTR-1 and GSTR-3B due "
            "dates including QRMP, input tax credit conditions under Section 16, blocked credits, "
            "e-way bills and e-invoicing."
        ),
        questions=[
            "When does a supplier of services need GST registration?",
            "What are the GSTR-3B due dates?",
            "What conditions must be met to claim input tax credit?",
        ],
        sections=[
            Section("About these notes", [DISCLAIMER]),
            Section(
                "1. Registration thresholds",
                [
                    "A supplier must register for GST when aggregate turnover in a financial year "
                    "exceeds ₹40 lakh for suppliers exclusively of goods, or ₹20 lakh for suppliers "
                    "of services. In special category states the limits are lower: ₹20 lakh for goods "
                    "in some states and ₹10 lakh for services.",
                    "Some persons must register regardless of turnover. These include anyone making "
                    "inter-state taxable supplies of goods, casual taxable persons, persons liable "
                    "under reverse charge, e-commerce operators and sellers supplying through them, "
                    "and non-resident taxable persons.",
                    "Aggregate turnover is computed on an all-India basis for a PAN and includes "
                    "taxable, exempt and export supplies, but excludes the GST itself.",
                ],
            ),
            Section(
                "2. Composition scheme",
                [
                    "Small taxpayers with aggregate turnover up to ₹1.5 crore (₹75 lakh in special "
                    "category states) may opt for the composition scheme. Tax is paid at a flat rate "
                    "on turnover: 1% for manufacturers and traders, and 5% for restaurants. Service "
                    "providers with turnover up to ₹50 lakh can use a separate scheme at 6%.",
                    "Composition taxpayers cannot collect GST from customers, cannot claim input tax "
                    "credit and cannot make inter-state outward supplies of goods. They pay tax "
                    "quarterly using CMP-08 by the 18th of the month after the quarter, and file an "
                    "annual return in GSTR-4 by 30 April.",
                ],
            ),
            Section(
                "3. Returns and due dates",
                [
                    "GSTR-1, the statement of outward supplies, is due by the 11th of the following "
                    "month for monthly filers. Taxpayers in the QRMP scheme (turnover up to ₹5 crore) "
                    "file it quarterly by the 13th of the month after the quarter.",
                    "GSTR-3B, the summary return through which tax is paid, is due by the 20th of the "
                    "following month for monthly filers. QRMP taxpayers file it quarterly by the 22nd "
                    "or 24th depending on their state, and pay tax in the first two months of each "
                    "quarter through form PMT-06.",
                    "The annual return GSTR-9 is due by 31 December of the next financial year. A late "
                    "fee of ₹50 per day (₹20 for nil returns) applies to a delayed GSTR-3B, and "
                    "interest at 18% per year is charged on tax paid late.",
                ],
            ),
            Section(
                "4. Input tax credit (Section 16)",
                [
                    "Input tax credit (ITC) lets a registered business reduce its output tax by the "
                    "GST paid on its purchases. Under Section 16 four conditions must all be met:",
                ],
                bullets=[
                    "The buyer holds a tax invoice or debit note",
                    "The goods or services have actually been received",
                    "The supplier has paid the tax to the government and the invoice appears in GSTR-2B",
                    "The buyer has filed its own return (GSTR-3B)",
                ],
            ),
            Section(
                "5. Time limits and blocked credits",
                [
                    "ITC for a financial year must be claimed by 30 November of the following year or "
                    "the date of filing the annual return, whichever is earlier. If the supplier is not "
                    "paid within 180 days of the invoice date, the credit must be reversed with "
                    "interest and can be reclaimed once paid.",
                    "Section 17(5) blocks credit on certain items regardless of business use, including "
                    "most motor vehicles, food and beverages, club memberships, and goods or services "
                    "for personal consumption.",
                ],
            ),
            Section(
                "6. E-way bills and e-invoicing",
                [
                    "An e-way bill is required to move goods worth more than ₹50,000 in a consignment. "
                    "It has Part A (invoice details) and Part B (vehicle details). For normal cargo the "
                    "validity is one day for every 200 km.",
                    "E-invoicing is mandatory for businesses whose aggregate turnover in any year since "
                    "2017-18 exceeds the notified threshold, currently ₹5 crore. Each B2B invoice must "
                    "be reported to the Invoice Registration Portal, which returns an Invoice Reference "
                    "Number (IRN) and a QR code.",
                ],
            ),
        ],
    ),
    DemoDoc(
        filename="TDS-Quick-Reference.md",
        title="TDS Quick Reference",
        kind="md",
        summary=(
            "A quick reference for common TDS sections (salary, interest, contractors, professional "
            "fees, rent and commission) with indicative rates and thresholds, deposit and return "
            "due dates, and certificates."
        ),
        questions=[
            "What TDS rate applies to rent for a building?",
            "When must TDS be deposited?",
            "What is the TDS rate for professional fees?",
        ],
        sections=[
            Section("About these notes", [DISCLAIMER]),
            Section(
                "Section 192: Salary",
                [
                    "Employers deduct TDS on salary at the employee's average slab rate under the "
                    "regime the employee chooses. Employees declare their regime and investments to "
                    "the employer at the start of the year.",
                ],
            ),
            Section(
                "Section 194A: Interest other than on securities",
                [
                    "Banks deduct 10% TDS on interest when it exceeds ₹50,000 in a year (₹1,00,000 for "
                    "senior citizens). For other payers the threshold is ₹10,000. Forms 15G and 15H let "
                    "eligible individuals with no tax liability avoid the deduction.",
                ],
            ),
            Section(
                "Section 194C: Contractors",
                [
                    "Payments to contractors attract TDS at 1% when the payee is an individual or HUF "
                    "and 2% for others. TDS applies when a single payment exceeds ₹30,000 or total "
                    "payments in the year exceed ₹1,00,000.",
                ],
            ),
            Section(
                "Section 194J: Professional and technical fees",
                [
                    "Fees for professional services attract TDS at 10%, while fees for technical "
                    "services, royalty for films and call-centre services attract 2%. The threshold is "
                    "₹50,000 per year for each category.",
                ],
            ),
            Section(
                "Section 194-I: Rent",
                [
                    "Rent for land, building or furniture attracts TDS at 10%, and rent for plant and "
                    "machinery at 2%. TDS applies when rent exceeds ₹50,000 for a month or part of a "
                    "month. Individuals not liable to tax audit who pay rent above ₹50,000 a month use "
                    "Section 194-IB instead.",
                ],
            ),
            Section(
                "Section 194H: Commission and brokerage",
                [
                    "Commission and brokerage attract TDS at 2% once payments exceed ₹20,000 in a year.",
                ],
            ),
            Section(
                "Deposit, returns and certificates",
                [
                    "TDS deducted in a month must be deposited by the 7th of the next month; TDS "
                    "deducted in March can be deposited until 30 April. If the payee has no PAN, "
                    "Section 206AA requires deduction at 20% or the normal rate, whichever is higher.",
                    "Quarterly TDS returns are filed in Form 24Q for salary and Form 26Q for other "
                    "payments, by 31 July, 31 October, 31 January and 31 May. Employers issue Form 16 "
                    "to employees by 15 June; other deductors issue Form 16A every quarter.",
                ],
            ),
        ],
    ),
    DemoDoc(
        filename="Scanned-ITR-Filing-Circular.pdf",
        title="Circular: Return filing timelines (scanned copy)",
        kind="pdf",
        scanned=True,
        summary=(
            "A scanned circular on income tax return deadlines: the 31 July due date for "
            "non-audit cases, belated and revised returns by 31 December, and late fees under "
            "Section 234F."
        ),
        questions=[
            "What is the late fee for filing the income tax return after the due date?",
            "Until when can a belated return be filed?",
        ],
        sections=[
            Section(
                "Return filing timelines",
                [
                    "Individuals whose accounts are not required to be audited must file their income "
                    "tax return by 31 July of the assessment year. Taxpayers subject to audit file by "
                    "31 October.",
                    "A belated return can be filed until 31 December of the assessment year. A return "
                    "can also be revised until the same date if a mistake is discovered.",
                    "Section 234F levies a late filing fee of ₹5,000. The fee is reduced to ₹1,000 when "
                    "total income does not exceed ₹5 lakh.",
                ],
            ),
        ],
    ),
]


ENGINEERING_DOCS: list[DemoDoc] = [
    DemoDoc(
        filename="Incident-Response-Runbook.md",
        title="Incident Response Runbook",
        kind="md",
        summary=(
            "How the team detects, triages and resolves production incidents: severity levels "
            "SEV1 to SEV4, on-call roles, the first 15 minutes, communication cadence, and "
            "blameless postmortems."
        ),
        questions=[
            "What should I do in the first 15 minutes of a SEV1?",
            "How often do we post status updates during an incident?",
            "When is a postmortem required?",
        ],
        sections=[
            Section(
                "Severity levels",
                ["Every incident gets a severity as soon as it is declared:"],
                bullets=[
                    "SEV1: full outage or data loss for many customers; page the on-call and the incident commander immediately",
                    "SEV2: a core feature degraded for many users, or an outage with a workaround",
                    "SEV3: a minor feature broken, limited customer impact",
                    "SEV4: cosmetic issue or internal tooling problem",
                ],
            ),
            Section(
                "Roles",
                [
                    "The incident commander (IC) coordinates the response and makes decisions; they do "
                    "not debug. The operations lead investigates and applies fixes. The communications "
                    "lead updates the status page and stakeholders. For SEV3 and SEV4 one engineer can "
                    "hold all roles.",
                ],
            ),
            Section(
                "The first 15 minutes of a SEV1",
                [
                    "Declare the incident in the #incidents Slack channel with the /incident command, "
                    "which creates a dedicated channel and a video bridge. Page the incident commander. "
                    "Post the first customer-facing status update within 15 minutes, even if the cause "
                    "is unknown.",
                    "Prefer mitigation over root cause: roll back the latest deploy, disable the feature "
                    "flag, or fail over to the secondary region before investigating deeply.",
                ],
            ),
            Section(
                "Communication cadence",
                [
                    "During a SEV1, post status updates every 30 minutes; during a SEV2, every hour. "
                    "Each update states the impact, what we are doing, and the time of the next update.",
                ],
            ),
            Section(
                "Postmortems",
                [
                    "A blameless postmortem is required for every SEV1 and SEV2 and must be published "
                    "within five working days. It includes a timeline, the root cause, what went well, "
                    "and action items with owners and due dates. Focus on systems and processes, never "
                    "on individuals.",
                ],
            ),
        ],
    ),
    DemoDoc(
        filename="API-Design-Guidelines.docx",
        title="API Design Guidelines",
        kind="docx",
        summary=(
            "Conventions for public REST APIs: resource naming, versioning, cursor pagination, a "
            "single error format, idempotency keys, authentication and rate limiting."
        ),
        questions=[
            "Which pagination style should new APIs use?",
            "What format should API errors have?",
            "How do we version our APIs?",
        ],
        sections=[
            Section(
                "Resource naming",
                [
                    "Use plural nouns for collections (/invoices) and nest at most one level "
                    "(/invoices/{id}/lines). Use kebab-case in paths and snake_case in JSON bodies.",
                ],
            ),
            Section(
                "Versioning",
                [
                    "Version the URL with a major version prefix such as /v1. Additive changes "
                    "(new optional fields, new endpoints) do not need a new version. Breaking changes "
                    "require /v2 and at least six months of overlap with a deprecation header.",
                ],
            ),
            Section(
                "Pagination",
                [
                    "All list endpoints use cursor pagination with ?limit= and ?cursor= parameters and "
                    "return next_cursor in the response. Offset pagination is not allowed for new APIs "
                    "because it is slow on large tables and returns duplicates when rows are inserted. "
                    "The default limit is 20 and the maximum is 100.",
                ],
            ),
            Section(
                "Errors",
                [
                    "Every error uses one JSON shape: an error object with code, message and "
                    "request_id. Codes are stable machine-readable strings such as validation_error or "
                    "rate_limited; messages are for humans. Never return stack traces.",
                ],
            ),
            Section(
                "Idempotency and rate limits",
                [
                    "POST endpoints that create money movements accept an Idempotency-Key header; a "
                    "retried request with the same key returns the original result. Rate-limited "
                    "responses use HTTP 429 with a Retry-After header.",
                ],
            ),
            Section(
                "Authentication",
                [
                    "Public APIs use OAuth 2.0 client credentials and short-lived bearer tokens. "
                    "Internal service-to-service calls use mTLS. API keys are only for legacy "
                    "integrations and must be rotated every 90 days.",
                ],
            ),
        ],
    ),
    DemoDoc(
        filename="Deployment-Checklist.pdf",
        title="Production Deployment Checklist",
        kind="pdf",
        summary=(
            "Steps before, during and after a production release: CI and review gates, "
            "backward-compatible migrations, canary rollout, monitoring and the rollback procedure."
        ),
        questions=[
            "How do we roll back a bad deploy?",
            "What must be true before deploying to production?",
            "How should database migrations be written?",
        ],
        sections=[
            Section(
                "Before deploying",
                ["Confirm every item before a production release:"],
                bullets=[
                    "CI is green on the exact commit being deployed",
                    "The pull request has at least one approving review",
                    "Feature flags for unfinished work are off by default",
                    "The on-call engineer for the service knows a deploy is happening",
                    "No deploys on Friday after 3 pm or during a declared incident",
                ],
            ),
            Section(
                "Database migrations",
                [
                    "Migrations must be backward compatible with the currently running code, because "
                    "old and new versions run side by side during a rollout. Use the expand and "
                    "contract pattern: add new columns as nullable, backfill in batches, switch reads, "
                    "then drop old columns in a later release. Never rename a column in one step.",
                ],
            ),
            Section(
                "Rollout",
                [
                    "Deploy to the canary (5% of traffic) first and watch error rate, p95 latency and "
                    "saturation dashboards for 15 minutes. Promote to 100% only if every metric stays "
                    "within its normal range.",
                ],
            ),
            Section(
                "Rollback",
                [
                    "If error rate or latency regresses, roll back immediately; investigate afterwards. "
                    "Run the deploy pipeline's rollback job, which redeploys the previous image tag, "
                    "then confirm the dashboards recover. Database migrations are not rolled back "
                    "automatically, which is why they must be backward compatible.",
                ],
            ),
        ],
    ),
    DemoDoc(
        filename="Engineering-Onboarding-Guide.md",
        title="Engineering Onboarding Guide",
        kind="md",
        summary=(
            "What a new engineer does in their first two weeks: access requests, local setup, the "
            "code review process, on-call shadowing and who to ask for help."
        ),
        questions=[
            "What should a new engineer do in the first week?",
            "How does code review work here?",
            "When do new engineers join the on-call rotation?",
        ],
        sections=[
            Section(
                "Week one",
                [
                    "Request access to GitHub, the cloud console (read-only) and the observability "
                    "stack through the IT portal on day one. Set up the local environment with the "
                    "repository's make setup command and ship a small documentation fix to learn the "
                    "pull request flow.",
                ],
            ),
            Section(
                "Code review",
                [
                    "Every change needs one approving review from a code owner. Keep pull requests "
                    "under 400 lines where possible, and reviewers aim to respond within one working "
                    "day. Use suggestions for small fixes and comment on intent, not style; formatting "
                    "is enforced by CI.",
                ],
            ),
            Section(
                "On-call",
                [
                    "New engineers shadow two on-call shifts in their second month and join the "
                    "rotation in their third month. Read the incident response runbook before the "
                    "first shadow shift.",
                ],
            ),
            Section(
                "Getting help",
                [
                    "Ask in the #eng-help channel; questions are welcome. Your onboarding buddy is the "
                    "first point of contact for anything about tools, process or people.",
                ],
            ),
        ],
    ),
]
