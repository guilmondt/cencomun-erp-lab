# Cencomun Core Test Specification

## Evaluation profile and approval boundary
Reuse this specification, ACCEPTANCE_CRITERIA and COMPARISON_PROTOCOL for the
same reproducible comparison in both ERPs. Confirmed user requirements below
remain authoritative. Unspecified behavior is proposed as LAB-ONLY-v1 in
tasks/100-ccm-core-test.md, explicitly distinct from production policy. The
business questionnaire is suspended; unanswered production decisions do not
block the synthetic evaluation. The user explicitly approved LAB-ONLY-v1 and
authorized Frappe implementation/execution on lab/frappe-baseline (ADR-010).
Production adoption, main changes and Axelor changes remain outside this task.
See ADR-008 and the complete reviewed ExecPlan.
The report may close with justified, documented technical limitations. Blocked
criteria retain BLOCKED and never count as passed; approving a platform still
requires all 14 mandatory criteria. See ADR-009 and the ExecPlan closing policy.

## Product extension
Add marketplace_enabled, cashea_enabled, cashea_price, supplier_reference,
warranty_quantity, warranty_unit, and condition to the standard product/item
entity. Must be searchable, permission-aware, API-visible, version-controlled,
and require no upstream core modification.

Warranty is stored as a non-negative integer quantity plus an explicit unit
(DAY, MONTH, YEAR), mapped to Cashea's Dias, Meses, Años. Preserve the original
quantity/unit pair; do not silently convert days to months or years to months.
A quantity of 0 means no warranty, regardless of the accompanying unit. This
replaces the earlier warranty_months-only representation by explicit user
decision; the same rule applies to Frappe and Axelor. See ADR-003 in
docs/DECISIONS.md. This defines duration data, not a warranty claim process or
a rule for when coverage starts.

Financing eligibility is independent of marketplace visibility: a paused
publication may still be sold with Cashea in the physical store. cashea_price
is the final product price in USD, including taxes, and is retained when
cashea_enabled is disabled. Ordinary product/sale prices must be positive.
Keep supplier_reference separately from the internal SKU when the codes differ.
See ADR-004. The manager-authorized zero-price accessories bundled with a paid
main product, their inventory costing and fiscal-print representation are
explicitly deferred; do not implement that exception in this Core Test phase.

## Cashea Order
Create header + lines with customer, datetime, currency, status, commission, shipping, gross total, net amount, cost, margin; lines contain product, qty, unit sell price, unit cost, line total.
Cashea order line quantities are whole units; fractional quantities are not
allowed. Apply this same validation in both platforms.
Distinguish store versus online sales and preserve the financed amount. The
commission consists of 4% for store sales or 6% for online sales, plus another
4% of the financed amount. The user confirmed that the first percentage is
applied to the total price of the products, including taxes. Store commission
= 0.04 * product total + 0.04 * financed amount; online commission
= 0.06 * product total + 0.04 * financed amount. Keep both bases explicit;
do not replace this formula with a single rate on the financed amount.

Use the ERP's supported product cost as the authoritative cost; do not add a
custom approval/creation/dispatch cost-selection policy. Product costs cannot
be negative. Cashea commissions are selling expenses, separate from product
cost; merchant-paid delivery is also a separate expense and does not change
the cost of the item.

Delivery and shipping-guide arrangements apply to Cashea web orders only.
Cashea store sales are sold and handed directly to the customer in the store;
do not require a shipping guide or carrier dispatch for that channel. For web
orders, the user confirmed that Cencomun absorbs delivery and does not charge
it to the customer. Therefore gross = final product total. Cashea deducts the
delivery expense from settlement; the net sale amount after both deductions is
gross - commission - merchant delivery expense. Preserve product cost,
commission expense and delivery
expense separately. The result after these selling expenses is
gross - ERP product cost - commission expense - merchant delivery expense,
equivalently net after both deductions - ERP product cost. Count each
expense once and report the result as amount and percentage of sales; do not
label selling expenses as inventory cost. Cashea charges delivery to Cencomun
under the supplied MRW weight tariff. Its deduction pays that expense; do not
record an additional separate payment or expense merely because a supporting
invoice exists. This aggregate net-sale calculation does not determine the
split between direct customer payments and Cashea transfers. Use known tariff
amounts in fixtures; an automated carrier quotation engine is outside the
existing Core Test scope. See ADR-005.

Include the same positive, price-inclusive synthetic tax case in both ERPs:
TAX01 STORE/WEB, 10% included, final product total 137.50 USD, revenue excluding
tax 125.00 and tax liability 12.50; financed amount 82.50, product cost 70.00.
Store commission 8.80; web commission 11.55 plus merchant shipping 0.70.
Post native invoices, inventory cost, payments and separate expense/tax accounts.
Verify the exact entries, balances and repeat protection in the ExecPlan.
The confirmed gross-based Cashea indicator is distinct from accounting profit
when gross includes tax: tax collected is a liability, not revenue or expense.
Accounting result in this lab case is 46.20 STORE / 42.75 WEB. This synthetic
tax is not a production tax rate or a fiscal-localization implementation.

Proposed technical state mapping for LAB-ONLY-v1:
WEB: NEW -> REVIEWED -> APPROVED -> PREPARING -> SHIPPED -> SETTLED.
STORE: NEW -> REVIEWED -> APPROVED -> FULFILLED -> SETTLED.
FULFILLED is direct store handover, not carrier shipping. REVIEWED represents
technical validation and APPROVED simulated Cashea acceptance, not a new
merchant manual-approval requirement. Proposed lab REJECTED paths start at
NEW/REVIEWED; CANCELLED is permitted before physical handover/dispatch only.
Detailed effects and invalid transitions are specified in the ExecPlan. These
are technical evaluation assumptions, not confirmed Cashea production rules.
Operational clarification: for Cashea web only, the user receives an order with
its shipping guide from Cashea and performs the physical dispatch. Cashea
manages the shipping arrangements/guide. Cashea store sales have direct sale
and handover in the store. Do not invent a merchant-operated carrier or manual
approval workflow. The states above are the proposed shared test representation
and explicitly distinguish web dispatch from direct store handover. Actual
production cancellation/rejection policy remains deferred; the lab mapping
does not require another business answer to proceed after plan review.
Do not require carrier shipping for store sales or ignore order-state validation
in either channel. See ADR-007.

## Cash session/closing
Support expected sales, USD cash, VES cash, POS/card, bank transfer, Cashea/marketplace, refunds/adjustments, expected vs actual, difference, confirmation/audit. Confirmed close cannot be silently edited.

## Purchase approval
<=200 USD buyer; >200 to 1000 manager; >1000 director. Deterministic and tested through the platform's recommended approval mechanism.

## Bank import/reconciliation
Import synthetic account/date/reference/currency/amount/description CSV. Support exact, probable, ambiguous, duplicate, and unmatched cases.

## API / events / MCP
Implement the neutral adapter contract. Expose reliable integration events for Cashea approved, cash closing confirmed, purchase approved. Prove an external MCP service can safely invoke deterministic operations.

## Search
Validate native search for product code/name, customer phone/name, invoice/reference, serial/supplier reference where supported.

## Monetary precision and conversion
Prices and monetary totals use at most two decimal places; exchange rates use
up to six. Round each line with decimal half-up rounding and sum the rounded
lines. Use the exchange rate applicable on the payment date. A missing rate
requires authorization to enter it manually; do not silently reuse an older
rate. The lab proposes manager authorization and separate date/rate evidence
for each synthetic payment. Production authorizing roles and split-payment
policies remain deferred. Shipping is quoted in USD and billed in VES at the official BCV rate
specified by the user-supplied tariff. See ADR-006. No rates, rules or platform
implementations are changed by this documentation update.
