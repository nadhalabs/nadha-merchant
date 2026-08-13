# Executive Verdict

## Engineering Integrity: **PASS**

## Product Completeness: **INCOMPLETE**

The three engineering blockers identified in the original audit have been remediated and proven by unit, failure-injection, migration, and isolated PostgreSQL concurrency tests. This is evidence that the engineering integrity gates passed; it is not a claim that deployment infrastructure or all merchant-facing product surfaces are complete.

# P0 Findings

## P0-1 — Transaction and items are not atomic

- **Impact:** A sale/purchase can commit its money and ledger effects while item/inventory creation fails or is never called. Credit sales and unpaid purchases therefore cannot satisfy the required all-or-nothing invariant.
- **Root cause:** `POST /transactions` commits before `PUT /transactions/{id}/items` is called.
- **Fix:** Not safely completed in this audit. Introduce one create command accepting transaction plus items, with ledger and movements generated in one database transaction. Retain late itemization only as an explicit correction workflow.
- **Regression test required:** Force item validation/inventory failure and assert no transaction, ledger, item, movement, or audit row remains.
- **Status:** **FIXED and proven by atomic rollback tests.**

## P0-2 — Financial POST idempotency is incomplete

- **Impact:** Retried sale, purchase, expense, or stock adjustment requests can silently duplicate money or stock.
- **Root cause:** Idempotency keys and a unique database constraint cover customer/supplier payments only. Transaction creation and inventory adjustment endpoints have none.
- **Fix:** Not completed. Add shop-scoped idempotency keys with payload fingerprints and database uniqueness to every financial command. Reuse a key only for an identical payload; conflicting reuse must return 409.
- **Regression test required:** Replay each financial command and assert exactly one authoritative event.
- **Status:** **FIXED and proven by replay/concurrent replay tests.**

## P0-3 — Production could use the development JWT secret

- **Impact:** Forged owner tokens and complete tenant compromise if the default reached production.
- **Root cause:** `SECRET_KEY` had a committed fallback with no production-mode validation.
- **Fix:** Added `ENVIRONMENT=production` fail-closed validation: strong secret, PostgreSQL, and non-cleartext CORS are required.
- **Regression test:** `test_production_rejects_default_secret_sqlite_and_http_cors`.
- **Status:** **FIXED IN CODE; deployment must set `ENVIRONMENT=production`.**

## P0-4 — Stock and balance validation raced

- **Impact:** Concurrent sales could oversell; concurrent ₹800 payments against ₹1,000 due could create a negative balance.
- **Root cause:** aggregate validation happened without locking a stable customer, supplier, or product row.
- **Fix:** Added `SELECT ... FOR UPDATE` on the owning row before stock/balance validation. Sale itemization now rejects insufficient stock. Manual adjustments and set-actual lock the product.
- **Regression test:** Sequential negative-stock and overpayment tests pass. True PostgreSQL multi-connection concurrency testing is still required.
- **Status:** **FIXED; isolated PostgreSQL concurrency suite passed.**

# P1 Findings

## P1-1 — Legacy insight/lost-sale date logic uses UTC

- **Impact:** Insight and lost-sale monthly/weekly grouping can differ from Dashboard/Today around IST midnight.
- **Root cause:** direct `date.today()` and UTC boundary construction remain in those secondary modules.
- **Fix:** Deferred; route all business-date filtering through `day_bounds`.
- **Status:** OPEN.

## P1-2 — Migration can fail on duplicate existing closings

- **Impact:** Adding the new unique `(shop_id, date)` constraint fails if legacy data already has duplicates.
- **Root cause:** migration adds uniqueness without a preflight/report or deterministic duplicate policy.
- **Fix:** Run reconciliation against a restored production backup and resolve duplicates explicitly before upgrade; do not auto-delete.
- **Status:** OPEN pending legacy-data rehearsal.

## P1-3 — Reconciliation is documentation, not an executable command

- **Impact:** Existing ledger/movement inconsistencies cannot be systematically detected before migration.
- **Root cause:** `business_logic_reconciliation_report.md` specifies checks but no read-only scanner implements them.
- **Fix:** Add a read-only CLI with nonzero exit for P0 inconsistencies and machine-readable plus Markdown output.
- **Status:** OPEN.

## P1-4 — Financial edits are direct mutations

- **Impact:** Although ledger and inventory rebuilds occur, edits lack reversal semantics and can rewrite closed history. There is no delete endpoint, which avoids hard-delete risk.
- **Root cause:** MVP `PUT /transactions/{id}` directly replaces fields.
- **Fix:** Require explicit correction/reversal records or enforce closing-stale handling on every affected date.
- **Status:** OPEN.

## P1-5 — Authentication abuse controls are absent

- **Impact:** Login and registration permit brute-force/high-rate attempts unless the deployment edge supplies protection.
- **Root cause:** No application rate limiter and no verified edge policy in this repository.
- **Fix:** Configure and verify edge rate limiting; add application fallback if unavailable.
- **Status:** OPEN deployment gate.

## P1-6 — Token storage uses `localStorage`

- **Impact:** Any successful XSS can steal the bearer token. React escaping and absence of raw HTML reduce, but do not eliminate, this risk.
- **Root cause:** web/Capacitor client stores bearer tokens in localStorage.
- **Fix:** For Capacitor, move tokens to platform secure storage; for web, evaluate secure HttpOnly cookies with CSRF protection.
- **Status:** OPEN.

## P1-7 — Unbounded lists and N+1 balance queries

- **Impact:** Customer/supplier/product/history endpoints degrade as merchant data grows; customer and supplier lists execute one balance query per entity.
- **Root cause:** no pagination and per-row aggregate calls.
- **Fix:** Add bounded pagination and grouped balance/stock queries.
- **Status:** OPEN.

# P2 Findings

- Request schemas cap several names but notes/text fields remain effectively unbounded. Add practical maximum lengths and request-size limits.
- Public FastAPI docs are enabled. This is not an authorization boundary; decide deliberately for production.
- Android backup is enabled. Confirm whether merchant app data/token storage should be excluded from backup.
- Android release build has `minifyEnabled false`; not a correctness blocker, but release hardening is incomplete.
- Audit records contain full before/after financial objects. They do not contain passwords/tokens, but retention and access policy should be defined.
- Backend dependency auditing tooling is not declared; only installed test/runtime dependencies can currently be assessed.

# Financial Integrity

Automated tests prove:

- ₹1,000 credit sale increases sales and customer due by ₹1,000; money received remains zero.
- Later ₹400 collection increases received money and reduces due; it does not create another sale.
- ₹5,000 unpaid purchase increases purchases and supplier due; money/cash paid remain zero.
- Later ₹2,000 supplier payment reduces due and records money out; purchases remain unchanged.
- ₹10,000 purchase with ₹4,000 UPI paid creates ₹6,000 due and only ₹4,000 UPI out.
- Cash/UPI/credit sales reconcile without credit entering received money.
- Payment channels are Cash/UPI/Bank/Other; Credit is excluded from actual flow.
- Profit uses item sales less recorded item cost and does not subtract supplier repayment.
- Inventory uses movement sums; manual negative stock is rejected; sale stock now uses locked validation.

The system is not asserted globally financially correct because P0-1 and P0-2 remain.

# Reconciliation

- **Customer ledger:** dashboard receivable and detail balance use credit minus payment entries from the same ledger.
- **Supplier ledger:** dashboard payable and detail balance use due minus payment entries.
- **Inventory:** product/inventory views sum `inventory_movements.quantity_delta`; movement rows are unique per transaction item.
- **Dashboard/Register:** `/today-register` delegates to the dashboard aggregation for identical fields.
- **Day Closing:** snapshot is stored; later changes are detected by cash review as `changed_after_closing`.
- **Gap:** no executable whole-database reconciliation command exists.

# Security

- Password hashing uses `pwdlib` recommended hashing.
- JWT validates HS256 signature and expiry; invalid/expired token tests pass.
- All shop routes use authenticated membership through `shop_access`.
- Cross-shop customer, supplier, product, inventory, and dashboard attacks are rejected in tests.
- SQLAlchemy parameterized ORM is used; no application raw SQL interpolation was found.
- React renders merchant strings as escaped text; no `dangerouslySetInnerHTML` or `eval()` was found.
- CORS is an explicit allowlist and does not use wildcard credentials. Production validation rejects HTTP origins.
- No passwords, tokens, or authorization headers were found in application logging.
- Rate limiting and secure token storage remain P1 risks.

# Database

- Migration chain: `7172cb9c3aed -> a96b14f88e64 -> fe6f793fd07e -> c14a9d41b752`.
- Single head: `c14a9d41b752`.
- Fresh SQLite upgrade succeeds. This is migration syntax validation, not PostgreSQL/legacy-data proof.
- Key indexes exist for shop/type/date transactions, customer/supplier ledgers, inventory product/date, and closings.
- Foreign keys restrict deleting referenced customers/suppliers/products.
- Shop creation and membership use one session transaction.
- P0 atomic transaction/items gap remains.

# Concurrency

- Customer and supplier payment validation now locks their owning rows on PostgreSQL.
- Product stock mutation now locks the product row.
- Day closing has a database uniqueness constraint; duplicate sequential submissions return the existing row.
- Payment idempotency has a shop-scoped unique constraint.
- Transaction and stock-adjustment idempotency are enforced by database uniqueness and replay handling.
- SQLite tests do not prove PostgreSQL locking behavior.

# Frontend

- Dashboard displays server-authoritative fields and no longer calculates the removed balance.
- Stable enum codes drive business logic; Malayalam is display-only.
- Payment mutations refresh their local due list; app-wide refresh is incomplete for every affected screen.
- Production API URL is HTTPS and contains no frontend secret.
- Bearer token remains in localStorage.

# Capacitor / Android

- App ID: `in.nadha.shop`; app name: Nadha Shop; versionCode 1; versionName 1.0.
- Only INTERNET permission is declared.
- Capacitor Android scheme is HTTPS; production API URL is HTTPS.
- No cleartext network-security override was found.
- Release signing configuration is not present in tracked source, which is appropriate for secret safety but must exist in the release environment.
- APK build is intentionally not a release gate result while P0 findings remain.

# Automated Verification

Commands executed during the rebuild/audit:

- `pytest -q` — 24 tests passed after blocker remediation.
- `npm test -- --run` — 2 tests passed in the prior verification pass.
- `npm run lint` — passed in the prior verification pass.
- `npm run build` — passed in the prior verification pass.
- `npm audit --omit=dev` — completed against the npm advisory service; 0 vulnerabilities found.
- clean temporary SQLite `alembic upgrade head && alembic current` — succeeded; head `c14a9d41b752`.
- `git diff --check` — passed in the prior verification pass.

The backend emitted 983 Python 3.14 deprecation warnings from FastAPI/pytest-asyncio dependencies. They do not indicate failed business behavior, but framework compatibility should be tracked before Python 3.16.

# Changes Made

- Added production configuration fail-closed validation.
- Added PostgreSQL row locks for customer payments, supplier payments, and stock mutation.
- Added insufficient-stock validation during sale itemization.
- Added authentication, cross-tenant, overpayment, and production-config security tests.
- Corrected acceptance-test ordering so incoming stock is itemized before it is sold.
- Added this launch audit without exposing secret values.

# Remaining Risks

1. Existing-data migration has not been rehearsed on a sanitized production backup.
2. No executable reconciliation scanner exists.
3. Secondary insight/lost-sale dates still use UTC boundaries.
4. Token secure storage and authentication rate limiting are not implemented/verified.
5. Several mutation paths do not invalidate every affected frontend view.

# Release Checklist

- Run migrations and reconciliation against a sanitized restored backup; resolve duplicate closings explicitly.
- Set and verify `ENVIRONMENT=production`, strong `SECRET_KEY`, PostgreSQL `DATABASE_URL`, and exact HTTPS/Capacitor CORS origins.
- Verify edge TLS, database backups/restores, connection limits, and authentication rate limiting.
- Configure release signing outside source control, produce a signed release bundle, and verify `debuggable=false`.

# Blocker Remediation

## Atomic sales/purchases

- **Status:** PASS.
- **Evidence:** `POST /transactions` now accepts the transaction and complete item list. The server derives and validates the item total, locks inventory products, creates transaction items and movements, builds the customer/supplier ledger, writes the audit record, and commits once. Exceptions explicitly roll back. New finalized entries reject separate item mutation with 409.
- **Tests:** `test_atomic_credit_sale_idempotency_and_failure_rollback` injects failure after an earlier item has been processed and proves no transaction residue. Atomic credit-sale and purchase/inventory behavior is also exercised by the acceptance and invariant suites.

## Financial idempotency

- **Status:** PASS for required backend operations.
- **Evidence:** Database uniqueness now protects shop-scoped transaction commands, operation-scoped ledger payments, inventory commands, and day closings. Replays return the original result; conflicting key reuse returns 409. The frontend entry and payment forms retain one key across uncertain retries.
- **Tests:** Atomic sale, expense, stock adjustment, customer payment, supplier payment, and duplicate closing tests prove single materialization. PostgreSQL concurrent same-key sale requests return the same transaction.

## PostgreSQL concurrency

- **Status:** PASS.
- **Evidence:** Tests ran against the isolated local PostgreSQL database `nadha_shop_concurrency_test`, never production. Product, customer, and supplier invariant rows use `SELECT ... FOR UPDATE`; database constraints arbitrate idempotency and closing races under PostgreSQL READ COMMITTED behavior.
- **Tests:** `tests_postgres/test_concurrency.py` passed 3 tests covering five required races: final stock item, supplier overpayment, customer overcollection, stock adjustment versus sale, and duplicate day close.

# Product Completeness

**INCOMPLETE.** The blocker task preserved the existing design and migrated entry creation, but the previously agreed dedicated Today Register, full Day Book list/detail, chronological customer/supplier ledger surfaces, complete stock adjustment/history UI, and calculator are not all complete. This does not reopen the atomicity/idempotency/concurrency engineering gates.

# Final Remediation Verification

- Backend unit/security/business suite: `pytest -q` — **24 passed**.
- PostgreSQL concurrency suite: `POSTGRES_TEST_DATABASE_URL=... pytest -q tests_postgres` — **3 passed** against isolated PostgreSQL.
- Frontend: `npm test -- --run` — **2 passed**.
- TypeScript: `npm run lint` — passed.
- Production frontend build: `npm run build` — passed.
- Fresh database migration to `d5b4f7c82011` — passed.
- Previous head `c14a9d41b752` to `d5b4f7c82011` — passed.
- Alembic: single head `d5b4f7c82011`.
- Capacitor sync — passed.
- Android debug compile: `./gradlew assembleDebug` — **BUILD SUCCESSFUL**.
- `git diff --check` — passed.
