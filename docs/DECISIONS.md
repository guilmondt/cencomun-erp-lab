# Architecture Decision Log

## ADR-XXX — Title
- Date:
- Platform: Shared / Frappe / Axelor
- Status: Proposed / Accepted / Rejected / Superseded
- Context:
- Options considered:
- Decision:
- Consequences:
- Upgrade impact:
- Evidence/tests:

## ADR-001 — Frappe baseline without cloud database services
- Date: 2026-10-04
- Platform: Frappe
- Status: Accepted for the baseline task
- Context: Issue #2 requires an isolated custom-app skeleton; cloud policy
  reserves full ERP/database tests for a dedicated runner.
- Options considered: run the full ERP in cloud; create only source files;
  build and install the package in cloud and document the separate runner.
- Decision: use the tagged Frappe v16.36.1 app structure and a pinned Flit
  toolchain; test source and a clean wheel installation. Keep all Cencomun
  code under `labs/frappe/cencomun_erp`; require ERPNext through app hooks.
- Consequences: no upstream edits, business features, database-only artifacts
  or production secrets. Cloud validation proves packaging/registration
  resources, not Frappe site installation or ERP behavior. License and contact
  metadata are explicitly unselected/placeholder values, pending owner choice
  before distribution.
- Upgrade impact: future platform upgrades must rerun packaging checks and
  the dedicated-runner installation/registration and business regression tests.
- Evidence/tests: five tests against the editable package and the same five
  against a clean installed wheel; wheel built from sdist. See
  `reports/frappe-baseline.md` and `labs/frappe/FULL_STACK.md`.

## ADR-002 — User-authorized real-site validation in cloud
- Date: 2026-10-04
- Platform: Frappe
- Status: Accepted for the explicitly requested integral validation
- Context: the user requested real MariaDB/Redis/site validation equivalent
  to the completed Axelor validation, expanding the earlier DB-free setup.
- Decision: run isolated, loopback services under a user-owned `/workspace`
  prefix; use exact upstream commits, Python/Node/tool pins and dependency
  locks. Generate only local synthetic credentials and use supported Frappe
  document/authentication/queue APIs; implement no Cencomun business features.
- Consequences: full-stack setup works without root or Docker-in-Docker.
  MariaDB uses libaio fallback because cloud io_uring is unavailable. Preserve
  upstream source/locks; resolve banking frontend dependencies outside its
  checkout with a frozen local lock. No cross-branch merge is performed.
- Upgrade impact: retain these service/runtime pins and rerun real-site tests
  before any later upgrade. This is no accounting/production-readiness claim.
- Evidence/tests: 39 functional checks, real app/module registration, assets,
  worker execution, graceful restart/persistence and five skeleton tests passed.
  See `reports/frappe-integral.md` and `reports/frappe-integral-evidence.json`.

## ADR-003 — Preserve warranty quantity and unit; zero means no warranty
- Date: 2026-10-04 (America/Caracas)
- Platform: Shared / Frappe / Axelor
- Status: Accepted by explicit user response
- Context: the user-provided Cashea template separates warranty quantity from
  its unit (Dias, Meses, Años). The initial Core Test field warranty_months
  cannot preserve all those inputs faithfully.
- Options considered: preserve quantity + unit; restrict the Core Test to
  durations expressible in months. For zero: no warranty; invalid; dependent
  on product policy.
- Decision: the user selected quantity + unit and explicitly confirmed that
  0 means no warranty. Use warranty_quantity and warranty_unit as the shared
  field names, with a non-negative integer quantity and DAY/MONTH/YEAR units.
  Preserve the source pair; 30 DAY is not silently rewritten as 1 MONTH.
  Retain an accompanying unit for quantity zero without treating it as coverage.
- Consequences: replace warranty_months in the shared specification and planned
  fixtures. Apply identical input/output expectations to both platforms. Other
  product, financing, pricing and supplier-reference decisions remain pending;
  no warranty start date, claim handling or correction process is selected.
- Upgrade impact: future persistence, API, export and regression checks must
  retain both fields without changing units. No business schema has been
  implemented, so this documentation change performs no database migration.
- Evidence/tests: explicit user response in this conversation; Cashea template
  structure recorded in tasks/100-ccm-core-test.md. Future cases include 30 DAY,
  6 MONTH, 1 YEAR and zero quantities. Business tests are not implemented or run.

## ADR-004 — Product financing, final price and supplier identifiers
- Date: 2026-10-04 (America/Caracas)
- Platform: Shared / Frappe / Axelor
- Status: Accepted by explicit user response
- Decision: financing and marketplace visibility are independent. Product
  prices are final USD prices including taxes; retain the configured price when
  Cashea is disabled. Ordinary sale prices cannot be zero. Preserve internal
  SKU and supplier reference separately when they differ.
- Deferred exception: the user described manager-authorized zero-price bundle
  accessories whose value is included in the main product cost, with inventory
  discharge and comments on the principal fiscal item. The user explicitly
  postponed studying this behavior. It is recorded, not implemented or treated
  as an unrestricted zero-price sale or zero inventory cost.
- Consequences: D01 is resolved; permissions for other business actions and
  the bundle/fiscal design remain outside this decision.
- Evidence/tests: user response in chat; documentation and planned fixtures
  updated. No business tests, inventory changes or fiscal printing performed.

## ADR-005 — Cashea commission components and merchant shipping expense
- Date: 2026-10-04 (America/Caracas)
- Platform: Shared / Frappe / Axelor
- Status: Accepted for the clarified core calculations; other workflow/payment decisions remain separate
- Decision: base commission rate is 4% for store purchases and 6% for online
  purchases, with an additional 4% of the financed amount in both channels.
  In a follow-up response the user confirmed that the channel rate applies
  to the total product price, including taxes. Thus store commission is
  0.04 * product total + 0.04 * financed amount, and online commission is
  0.06 * product total + 0.04 * financed amount. Keep both components explicit;
  4% + 4% does not generally imply 8% of the financed amount.
  Example: products 100 USD, financed 60 USD -> 6.40 USD store / 8.40 USD online.
- Accepted formulas: gross = final product total; customer shipping charge = 0
  because the user confirmed that Cencomun absorbs delivery;
  net after commission = gross - commission. Product cost comes from the ERP; negative costs
  are not allowed. The user clarified that commissions are expenses. Withdraw
  the custom choice of cost at creation/approval/dispatch; use the native ERP
  cost as the authoritative product cost. Keep commission and delivery expenses
  separate from it. Result after selling expenses = gross - ERP product cost
  - commission expense - merchant delivery expense; report amount and percentage
  of sales. This does not assert that native ERP valuation can never change.
- Shipping: Cashea charges Cencomun. The user supplied an MRW national weight
  tariff in chat: amounts are USD and invoicing is VES at the official BCV rate.
  Use the merchant-payable amount, not the full coupon value. Do not reproduce
  the full vendor annex in the repository or infer a flat per-kg formula.
  Reference cases include 0.500 kg -> 0.70 USD, 1.000 kg -> 1.40 USD,
  7.000 kg -> 4.90 USD and 8.000 kg -> 5.60 USD. Handle the merchant expense
  once. The customer pays only the products; there is no shipping revenue.
  The user confirmed that Cashea deducts it from settlement. Net sale after
  both deductions = gross - commission - delivery expense; result after selling
  expenses = that net - ERP product cost. The deduction is payment of the one
  shipping expense, not an additional expense/payment.
- Quantity clarification (2026-10-05, America/Caracas): the user confirmed only
  whole-unit quantities in Cashea orders; fractional lines are rejected.
- Separate payment decisions: allocation of customer upfront payments versus
  Cashea transfers belongs to the payment/cash scenarios and is not inferred
  from the aggregate net-sale formula.
- Scope: use known supplied tariff amounts for Core Test fixtures. Packing
  rules, weight rounding and quotes outside the provided ranges would require
  separate definition if an automated quotation engine is later requested;
  such an engine is not required by the existing specification. Do not
  extrapolate the tariff or expand the project to implement it now.
- Evidence/tests: explicit user response and pasted annex. Conditional shared
  scenarios are in the ExecPlan; no order/commission/shipping tests executed.

## ADR-006 — Monetary precision, line rounding and payment-date exchange rate
- Date: 2026-10-04 (America/Caracas)
- Platform: Shared / Frappe / Axelor
- Status: Accepted; operational authorization details remain pending
- Decision: prices and totals have at most two decimals; exchange rates up to
  six. Round lines and sum rounded values using decimal half-up. Use the rate
  of the payment date; entering a missing rate manually requires authorization.
- Consequences: replace the earlier four-decimal unit-price proposal. A 0.005
  USD unit-price input is outside the approved precision. Rounding may still
  be needed on intermediate currency-conversion calculations. Freeze the
  applied rate as transaction evidence; do not silently substitute an older
  rate. This is not a decision on purchase approval rates before payment.
- Pending: authorizing role, audit requirements, source for each general
  operation and handling of payments across several dates. Shipping's BCV
  source is specified by the supplied tariff.
- Evidence/tests: explicit user response. Future cases must verify line sums,
  ties and exchange-rate dates identically; no calculations run in either ERP.

## ADR-007 — Cashea web dispatch versus direct store handover
- Date: 2026-10-05 (America/Caracas)
- Platform: Shared / Frappe / Axelor
- Status: Accepted operational clarification; exception mapping still pending
- Context: the question about REJECTED states was unclear to the user and
  conflated an internal test model with their actual shipping workflow.
- Decision: record the user's channel-specific process. For Cashea web only,
  receive the order with its guide from Cashea, then perform the shipment;
  Cashea manages the shipping arrangements and guide. Ordinary Cashea sales
  are sold and handed directly to the customer in the store. Do not require
  a guide or carrier dispatch for store sales. Do not assume the merchant
  chooses carrier rules or manually reviews/approves each order as proposed
  in the earlier interview.
- Consequences: keep the existing Core Test states and validation requirements,
  but map them to real channel-specific actions/events before implementation.
  CO00 represents direct store handover with no shipping expense; CO01 represents
  web dispatch with the already agreed merchant-paid shipping expense. The user
  has not approved particular production REJECTED/CANCELLED paths. The subsequent
  user instruction in ADR-008 suspends the interview and substitutes explicitly
  proposed laboratory assumptions for the technical comparison, preserving this
  confirmed channel distinction.
- Pending: what happens when a received web order cannot be dispatched, who can
  cancel it, how web dispatch is recorded and the remaining state/event mapping
  for each channel in production. The web shipping-exception question is
  suspended, not answered by omission; laboratory mapping is proposed in the plan.
- Evidence/tests: user's explanations and explicit distinction between Cashea
  web and direct store sales in chat; documentation only. No carrier integration,
  order workflow or acceptance test implemented.

## ADR-008 — Bounded comparison with explicit laboratory assumptions
- Date: 2026-10-05 (America/Caracas)
- Platform: Shared / Frappe / Axelor
- Status: Evaluation method accepted by user instruction; LAB-ONLY-v1 proposed
  for review; implementation not authorized
- Context: exhaustive production-policy clarification was blocking a technical
  comparison that can use deterministic synthetic cases. The user explicitly
  stopped the questionnaire, required preservation of all prior answers, and
  requested a bounded plan before implementation.
- Decision: keep the seven existing Core Test blocks, 14 acceptance criteria
  and comparison protocol. Preserve confirmed rules in ADR-003–007. Resolve
  remaining evaluation details with one versioned synthetic LAB-ONLY-v1 profile
  and identical fixtures/oracle for both ERPs; defer actual production decisions.
  Do not ask again for already answered rules or for issues a lab assumption
  can resolve. Review is not authorization to implement or production adoption.
- Proposed profile: store FULFILLED versus web SHIPPED with guide; simulated
  Cashea acceptance/settlement; native ERP inventory, cost, payments and expenses;
  explicit cash formulas, purchase approval base, bank matching, roles, rates,
  API/event/MCP contract, idempotency and deterministic benchmark dataset.
  Exact assumptions and expected outcomes are in tasks/100-ccm-core-test.md.
- Consequences: D04-A is suspended and requires no answer for this evaluation.
  Former D03–D08/T01/T02 production questions are deferred, not accepted by
  omission. No fake production policy, upstream changes, business SQL, relaxed
  permissions or changed monetary rules to obtain parity. Technical mapping
  targets existing ERPNext and Axelor entities/services; actual execution must
  prove native inventory/accounting effects and record missing capabilities.
- Completion: publish a terminal, reproducible result for every required case
  in both ERPs and protocol metrics, using the closing policy subsequently
  clarified in ADR-009. A failed or blocked platform criterion does not count
  as passed; approving its Core Test requires all mandatory criteria to pass.
  Preserve unsuccessful/unavailable results rather than changing the oracle.
- Evidence/tests: user instruction in chat; local ERPNext v16.36.1 DocType JSON
  and public Axelor v9.1.8 domain XML reviewed to verify target model names.
  Documentation/expected arithmetic only; no Core Test, upgrade, schema, data,
  contract implementation, Axelor branch or main change performed.

## ADR-009 — Inclusive synthetic tax and reports closed with limitations
- Date: 2026-10-05 (America/Caracas)
- Platform: Shared / Frappe / Axelor
- Status: Evaluation requirements accepted by user instruction; synthetic
  scenario proposed for plan review; implementation remains suspended
- Decision: add one common positive, price-inclusive tax scenario with store
  and web variants. LAB tax 10%, total 137.50 USD = revenue 125.00 + tax
  liability 12.50; financed 82.50 and ERP product cost 70.00. Commission uses
  the tax-inclusive total: store 8.80, web 11.55; web shipping 0.70 separately.
  Native ledger entries must distinguish revenue, tax payable, inventory/COGS,
  commissions, shipping and payments, with identical expected effects per ERP.
- Accounting distinction: preserve the confirmed gross-based Cashea indicator
  but do not call it accounting profit when it contains collected tax. Native
  accounting result excludes tax: 46.20 store / 42.75 web in the synthetic case.
  No production tax rate, extra tax on fees, fiscal remittance or localization
  rule is inferred. Exact fixtures, entries and repeat checks are in the plan.
- Closing: the comparison report may conclude with justified technical
  limitations, citing evidence, affected criteria/cases, diagnosis, supported
  attempts, impact and steps to resolve/verify. BLOCKED never counts as PASS;
  dependent UNRUN cases reference their blocker. Keep the denominator of 14
  criteria and do not claim full parity or an approved ERP without all mandatory
  checks passing. The common oracle is not relaxed for a blocked platform.
- Evidence/tests: explicit user instruction; native tax-related field names
  checked in ERPNext metadata and public Axelor domains. Documentation and
  expected arithmetic only; no implementation, migration, ERP test or upgrade.


## ADR-010 — Authorized Frappe Core Test with frozen LAB-only data

- Date: 2026-10-05
- Status: Accepted by explicit user instruction
- Context: User approved the corrected ExecPlan including TAX01 and closure
  with justified limitations, then explicitly requested implementation/execution.
- Decision: Implement only Cencomun extensions and isolated synthetic sites
  on lab/frappe-baseline. Freeze shared fixtures/oracle in fixtures/ccm-core-v1
  for an identical future Axelor run. Never promote synthetic rules to business
  policy. Do not modify main, the Axelor branch, production or upstream code.
- Consequences: All 14 criteria get evidence/status. Technical blockers stay
  BLOCKED and dependent scenarios UNRUN; independent tests continue. Previously
  recorded user answers remain authoritative and are not asked again.
- Implementation clarification: Native bank-book receipts use a distinct
  synthetic counterparty CBANK so C002 retains the agreed zero balance. Individual
  warehouses isolate economic snapshots; technical IDs are mapped separately.
  Benchmark IDs vary deterministically to measure real NEW creations rather
  than idempotent replays. These choices preserve the reviewed business oracle.

## ADR-011 — Correct mandatory Core Test coverage without changing business rules

- Date: 2026-10-05
- Status: Accepted by explicit user instruction
- Decision: Require parsed, useful before/after snapshots and reasons for
  state transitions, purchase approval/revision, cash confirmation, manual rate
  authorization and bank reconciliation. Automated steps use explicit LAB-only
  technical reasons; manual decisions retain the actor's supplied note.
- Coverage: Add unknown-state, preacceptance delivery, missing WEB guide and
  APPROVED/PREPARING cancellation cases. Test eight forbidden MCP actions on
  eligible objects through unavailable tools and the native RPC boundary;
  independently verify denial audit and unchanged native effects. Compare full
  API/MCP results in six routes and both creation/replay directions. Successfully
  deliver events before restarting the consumer and prove persisted deduplication
  using distinct reception/application counters.
- Reproducibility: The shared coverage revision 2 supplement fixes added IDs,
  inputs and expected outcomes for both ERP. Existing fixture/oracle bytes stay
  unchanged. Missing or prior-revision mandatory evidence cannot remain PASS;
  verified archival clears stale outputs before another complete run. Original
  attempts and evidence are preserved. This adds no production business policy.
- Limits: Patch criterion remains BLOCKED, dependent cases UNRUN; the incomplete
  official integration suite is documented separately from its four passing
  utility unit tests. No changes to main, Axelor, production or upstream source.

## ADR-012 — Isolate official server fixtures and distinguish cloud restoration

- Date: 2026-10-05 (America/Caracas)
- Status: Accepted by explicit technical continuation instruction from fcf690d
- Decision: Run official Frappe/ERPNext server discovery on empty upstream-only
  sites with their official bootstrap fixtures, preserving LAB lists and oracle.
  Copy a Bench at the pinned SHAs for command tests that alter global config or
  generate source files; keep the original Cencomun Bench/sources untouched.
  Start its own worker before RQ tests, using the Bench-specific queue prefix.
  Add only exact test extras under existing runtime constraints; record existing
  requests/oauthlib incompatibilities instead of silently changing pins.
- Evidence policy: Record official Ran N counters separately from discovery and
  JUnit outcome events. Class fixture failures and subtests can inflate JUnit
  records, never the executed-test count. Preserve failures/UNRUN methods and
  previous attempts. An interrupted ERPNext log collision is quarantined;
  exclusive attempt reservations and concurrency regression tests prevent reuse.
  Modular repetitions retain their scope and do not rewrite a failed full suite.
  The pinned ERPNext CI requires Payments. Its current develop requires Frappe
  17, so only the compatible official version-16 SHA
  cca07d9f9392e2ea0e521c5975151db9e4b6c321 is used as an isolated test fixture,
  with seven hashed SDK pins in official-payments.lock.txt. It is absent from
  the Cencomun Bench/venv/sites; existing packages and framework pins do not
  change. Repeat on a separate fresh official site using the native CI runner
  (one shard covering all modules; official bootstrap then ERPNext lightmode).
  Its own per-module Administrator reset is preserved without permission
  changes. Record native Tests counts and verbose outcomes separately from
  serial JUnit; keep original failures and unknown interrupted counts.
- Patch: Official Frappe and ERPNext 16.36 tags currently end at 16.36.1. Keep
  criterion 13 BLOCKED and all six dependent scenarios UNRUN. No minor upgrade
  is proposed or executed; such a change needs a separate reviewed plan.
- Cloud: The user already verified the saved catalog commit fcf690d. Do not
  save/publish again. Provide read-only verification instructions for an actual
  NEW cloud task: expected saved HEAD/pins/files, retained service startup and
  authenticated P001 price50.00/stock5 matched with native API records. Retain
  cloud verification UNRUN until evidence includes that new task's identity;
  same-machine site replay has separate scope.

## ADR-013 — Proven official preparation repairs and scoped follow-up

- Date: 2026-10-06 (UTC)
- Status: Accepted by explicit technical continuation from 8158b68
- Scope: Official copied Bench/sites and test harness only; no production rules,
  shared oracle, pins, original Cencomun runtime or upstream source changes.
- Decision: Rename the helper payments.py to prepare_payments.py because its
  import shadowed the pinned Payments package and produced an empty native
  module list. Verify package origins and native resolver entries; rebuild only
  the site's app_modules cache when a mismatch is demonstrated. Preserve the
  mistaken initial preflight as invalid preparation, not PASS.
- Fixture order: Insert the six exact pinned Currency Exchange JSON records
  through the native Document API before importing test modules/bootstrap.
  make_test_records imports ERPNextTestSuite and bootstraps masters too early
  on an empty site. Keep validators, fixture bytes/dates and allow_stale intact;
  retain failed sites/attempts rather than editing their persisted zero-cost BOMs.
- Transport: Reject external HTTP/DNS/socket operations before transport during
  reproductions. This is an explicit offline restriction, not a fabricated rate
  or provider response. Preserve historical ProxyError tunnel-403 evidence;
  disabled=0 and missing official rates are recorded. Historical logs without
  test IDs cannot be assigned unequivocally to individual cases. No new provider
  calls, network expansion, HOME workaround or minor upgrade is authorized.
- Evidence: Clean native CI auth 17 PASS, Payment Request 22 PASS, five-module
  sequence 126 PASS, BOM/negative-rate methods PASS and all 14 original division
  case IDs PASS in scoped executions. Keep both original full suites FAIL and
  criterion 13 BLOCKED with six UNRUN. Only new observed reproductions count in
  follow-up; remaining unexecuted events do not become PASS or inevitable blocks.
  Exact commands, attempts, diagnosis and next steps are published in
  reports/frappe-official-preparation-investigation.md. The acknowledged external
  cloud-restoration receipt is preserved byte-for-byte and is not repeated.

## ADR-014 — One final full CI pass with independent result provenance

- Date: 2026-10-06
- Status: Accepted by explicit user instruction from 9cbfbbd
- Decision: Execute one full native CI shard for Frappe followed by one for
  ERPNext, on new isolated official-only sites. Preserve all previous sites,
  attempts and generated sources. Refresh only the copied test sources to the
  same clean SHAs between applications. Keep native workflows, bootstrap,
  validators, assertions, pins, HOME and the shared oracle unchanged.
- Preparation: Apply the proven Payments helper/import repair and load the six
  exact official Currency Exchange records via native Document API before any
  ERPNext test import/bootstrap. Keep offline rejection enabled for preparation,
  discovery, workers and runners; do not fabricate provider responses or rates.
- Evidence: This full pass supplies its own native counters, result events by
  ID, skips, missing results and failure classifications. Earlier modular PASS
  never fills a missing result. Distinct IDs and repeated native executions are
  reported separately; discovery and fixture bootstrap execute zero tests.
- Reader repairs: Validate native class headers against the same discovery
  manifest and recognize outcomes appended to progress without a newline.
  Reparse the preserved log rather than rerunning tests. Keep initial derived
  records private, and cover both reader defects with regression controls.
- Limits: A demonstrated offline rejection is distinct from a provider response.
  A local TCP refusal demonstrates an unavailable endpoint at that instant,
  not its cause or an inevitable platform blocker. Attribute readonly HOME only
  with causal evidence in that attempt. Unknown causes remain UNKNOWN/FAIL.
  C13 remains BLOCKED and its six PATCH scenarios UNRUN; no minor change,
  cloud restoration repeat or additional full repetition is authorized here.
- Closure: Compare the original Cencomun runtime hashes and perform an
  authenticated price/stock read. Repeat its regression only if preparation
  changed that runtime. Preserve the scope of the earlier 34 mandatory groups;
  do not call the read-only check a new Core Test or cloud restoration.
- Evidence: tasks/102-frappe-official-final-ci.md and
  reports/frappe-official-final-ci.md; publish only sanitized evidence on
  lab/frappe-baseline with PR #4 remaining a draft.

## ADR-015 — bounded causes, native mocks and preservation after 618c676

- Scope: one isolated ERPNext revaluation method and nine affected/preceding
  Frappe modules. No complete repetition or oracle/pin/HOME/access changes.
- Accounting: observe native Journal Entry creation/rate resolution/submit.
  No eligible historical FX row in the test's date window; offline resolver
  returns zero, native journal fallback returns one, debit changes by 100 while
  loss row stays 8000. Keep ERROR; no invented rate or validator bypass.
- HTTP: correct own classifier. Responses' "Connection refused" is not OS
  TCP refusal. Preserve old diagnostic and publish a revision. Respect native
  in-memory Responses interceptors only without passthrough; reject real
  external requests, DNS and sockets. Never install a business mock or restart
  web during a method. Observe PID/start ticks, listener, effective URL and site.
- Results: old full results remain FAIL. Corrected bounded sequence 155 tests,
  139 PASS/1 FAIL/15 ERROR; remaining first causes UNKNOWN. Loader reference is
  the retained pinned discovery, not a new discovery run. Preserve bootstrap,
  class-fixture errors and initial derived coverage before revisions.
- Closure: original runtime/oracle/pins unchanged, authenticated price/stock
  read, Core scope remains its previous 34 groups. C13 BLOCKED/six PATCH UNRUN;
  external cloud restoration fcf690d remains separate and is not repeated.
- Environment: prepare only ordinary repository/ref/start instructions after
  testing/push, preserving network/secrets/variables/privacy/permissions. Draft
  persistence is distinct from coordinator Save/Publish and new restoration.
- Evidence: tasks/103-frappe-bounded-cause-diagnostics.md,
  reports/frappe-bounded-cause-diagnostics.md and docs/FRAPPE_ENVIRONMENT_START.md.
## ADR-016 — native credential precedence and bounded request/auth diagnosis

- Own preparation defect: pinned install_db prefers already loaded common
  admin_password to the command argument; writing a different per-site conf
  afterward made HTTP password login disagree with the stored native hash.
  New sites reuse the existing common credential. No existing password, secret,
  common config, policy or access is changed or reset.
- Read-only evidence: passlib verifies SELECT results, never check_password,
  with boolean matches only. Native request Local transitions, exception frames,
  configuration-loading time and redirect parameter names/presence are observed.
  No credential/token/cookie values or fake per-case request are published/added.
- Bounded outcomes: 14 of the 16 prior failures pass after new-site preparation;
  two Client retain ERROR. Their truthy native _dict request has cache_control
  None at website/utils:537 while the native Workflow fixture triggers print.
  No upstream fixture, assertion, renderer or validator change is made.
- OAuth's first reproduced login 500 is a native SecurityException from the IP
  failure tracker, preceding authorize's login redirect and empty token result.
  Performance's native benchmark runs without frame profiling; threshold intact.
- Extra API-key positive request FAIL remains UNKNOWN; stored native secret is
  not decryptable, but initial key/cache mutation order was not captured.
  Do not regenerate keys, repeat to force PASS or call UNKNOWN inevitable.
- All old results/attempts and full FAIL remain; original runtime/oracle unchanged,
  authenticated Core price/stock read passes, no Core rerun. C13 BLOCKED/six UNRUN.
  Coordinator already published baad8f9; only a new ordinary draft is prepared.
- Evidence: tasks/104-frappe-auth-request-diagnostics.md and
  reports/frappe-auth-request-diagnostics.md. PR #4 stays draft on lab only.

## ADR-017 — residual ID reconciliation and deferred offline HTTP guard

- Reconcile exactly the 56 full-run failures and two additional native Client
  errors. Later selected PASS never replaces or improves the full FAIL counters.
  UNRUN means no later method result; a read-only probe/subcase is not a PASS.
- Own demonstrated defect: eagerly importing requests in sitecustomize adds HTTP
  imports to non-HTTP RQ jobs. Install the identical wrapper when requests first
  imports; DNS/socket audit remains active from startup. Native mocks only without
  passthrough. Memory's retained 58 MiB FAIL becomes 52 MiB PASS, same native limit.
- Observe swallowed backup exceptions using type/errno/frame/HOME boolean only.
  New per-command errno30 proves HOME limitation; original generic exit1 does not.
- Native schema generated-column index drops/recreates despite zero-query assertion.
  Verify only the original subcase, no random resampling or assertion/source change.
  Native password restore option parsing and existing-user password contract retain
  FAIL; never repeat cases that change credentials or repair their retained state.
- Socket masks host-negative DB checks. Diagnostic TCP readiness fails before any
  native test; read-only native probe1130, only localhost grant, skip_name_resolve ON.
  Restore only new site's original socket; no access/grant/credential changes.
- API secret/key mismatch remains FAIL/UNKNOWN: existing ciphertext cannot decrypt
  with retained keys, no value-level initial cache/key chronology. No regeneration.
- Preserve full FAIL/ERROR/SKIP, four ERPNext FX errors, C13 BLOCKED/six PATCH UNRUN.
  Original runtime/oracle unchanged, authenticated read passes; no Core rerun.
  Coordinator already published678c5ef; only ordinary ref/start instructions drafted.
- Evidence: tasks/105-frappe-residual-failure-closure.md,
  reports/frappe-residual-failure-closure.md. PR #4 remains draft on lab only.
