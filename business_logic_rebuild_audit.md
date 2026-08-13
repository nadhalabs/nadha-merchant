# Nadha Shop business-logic rebuild audit

## Sources of truth found

- `transactions.amount` is the economic value of sales, purchases, and expenses.
- `transactions.paid_amount` plus the payment fields describe the immediately paid portion; it is not the transaction value.
- `ledger_entries` records customer credit/payment and supplier due/payment. Outstanding balances are credits or dues minus payments.
- `inventory_movements.quantity_delta` is the stock source of truth. Product forms correctly do not contain a mutable stock field.
- `day_closings.snapshot` is the permanent closing source. The old listing incorrectly recomputed live totals instead of returning it.

## Incorrect behaviour found before this rebuild

1. Dashboard `estimated_position = sales - purchases - expenses` subtracted unpaid purchases and presented an undefined “balance”. A ₹5,000 unpaid purchase could therefore reduce the display by ₹5,000 although no money moved.
2. Daily totals used UTC midnight. “Today” was wrong for the shop default timezone, Asia/Kolkata, around local midnight.
3. Customer and supplier payments had no payment method. Reports added all customer collections to expected cash and all supplier payments to cash out, even when they may have been UPI or bank payments.
4. Payment endpoints accepted amounts above the outstanding balance, allowing negative customer receivables and supplier payables.
5. Payment requests had no backend double-submit protection.
6. A paid/due purchase could report inconsistent `amount`, `paid_amount`, `payment_state`, and payment method. Due purchases did not require a supplier.
7. `credit_sales` subtracted `paid_amount` only for credit-method sales, while mixed and other paid states were interpreted differently elsewhere.
8. Expected cash combined actual cash receipts with channel-unknown ledger collections/payments.
9. Day Book listing recomputed each historic day from mutable transactions rather than returning the saved source snapshot.
10. Repeated Close Day calls created multiple snapshots for the same shop/date.
11. Manual inventory decreases could take tracked stock below zero. There was no set-actual operation that generated a correction delta.
12. Customer/supplier ledger screens had running balances but payment channel could not be explained to the merchant.
13. Transaction history date filters used UTC boundaries rather than the shop timezone.

## Authoritative definitions after rebuild

- Sales: full sale transaction amounts in the shop-local day, paid and unpaid.
- Money received: paid portions of sales plus customer payment ledger entries, grouped by their real channel.
- Customer receivable: customer-credit entries minus customer-payment entries.
- Purchases: full purchase transaction amounts, independent of payment timing.
- Supplier payable: supplier-due entries minus supplier-payment entries.
- Money paid: immediately paid purchase portions, paid expenses, and supplier payments, grouped by channel.
- Expected cash flow: cash received minus cash paid for the day. It is not advertised as cash in hand.
- Stock: sum of inventory movement deltas.
- Closing history: the serialized snapshot captured at Close Day, not a live recomputation.

## Legacy-data reconciliation policy

Existing channel-less payment entries remain channel-less; the migration does not guess whether they were Cash, UPI, Bank, or Other. They remain included in receivable/payable balances but cannot safely be assigned to channel flow. Ambiguous historical data is reported, not mutated.
