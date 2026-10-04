# Cencomun Core Test Specification

## Product extension
Add marketplace_enabled, cashea_enabled, cashea_price, supplier_reference, warranty_months, and condition to the standard product/item entity. Must be searchable, permission-aware, API-visible, version-controlled, and require no upstream core modification.

## Cashea Order
Create header + lines with customer, datetime, currency, status, commission, shipping, gross total, net amount, cost, margin; lines contain product, qty, unit sell price, unit cost, line total.
States: NEW -> REVIEWED -> APPROVED -> PREPARING -> SHIPPED -> SETTLED, with valid CANCELLED/REJECTED paths.

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
