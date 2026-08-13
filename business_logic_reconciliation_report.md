# Business logic reconciliation report

This repository contains local SQLite databases that may hold development or merchant data. No ambiguous historical financial records were modified.

Run the reconciliation checks against a deliberate database backup before production migration. Flag:

- credit sales without a matching `customer_credit` ledger entry;
- due purchases without a matching `supplier_due` entry;
- customer or supplier payments with no payment channel (legacy records);
- cumulative payments greater than their credit/due entries;
- duplicate transaction-linked ledger entries;
- inventory-enabled transaction items without an inventory movement;
- inventory movement totals below zero;
- orphan ledger entries and transaction items;
- duplicate day closings for the same shop-local date;
- any historic dashboard derived from `sales - purchases - expenses`.

The new migration preserves rows and adds nullable payment-channel/idempotency fields. Null legacy channels are intentionally not backfilled because their values cannot be inferred safely.
