# Nadha Merchant mobile UX audit

Audit date: 2026-08-13

Scope: frontend architecture, app shell, navigation, authentication, dashboard, sales/expenses/purchases, credit, people, products, history, product itemization, loading/empty/error/success states, forms, theme, language, and API error handling. The current frontend is React 19 + TypeScript + Vite with plain CSS and Capacitor; it has no router or UI framework. The audit therefore recommends reusable React primitives and CSS tokens that preserve the existing architecture.

## P0 — confusing, broken, or dangerous

1. **Logout happens immediately and clears all local storage.** The header icon has no accessible name, explanation, or confirmation and can be tapped accidentally. `localStorage.clear()` also deletes unrelated preferences.
2. **Raw backend and browser errors reach merchants.** The API client throws `body.detail`, `Failed to fetch`, and validation payloads directly. Forms render those strings without safe mapping or recovery guidance.
3. **Authentication/session expiry is not handled centrally.** A 401 after startup does not reliably clear only the session and return to sign-in with a helpful message.
4. **Important async actions permit duplicate submissions and often fail silently.** Payment, closing, product, people, lost-sale, itemization, and edit actions lack consistent busy, success, and error states.
5. **There is no Settings destination, language preference, or appearance preference.** Malayalam, dark mode, system appearance, and the required logout experience are absent.
6. **Many list-loading failures become unhandled promise rejections or blank screens.** Merchants cannot distinguish empty data from a connection problem or retry.

## P1 — materially damages usability

1. **The 76px branded header consumes prime phone space.** It repeats an uppercase slogan on every screen and uses an ambiguous arrow glyph for logout.
2. **Navigation exposes structure instead of the clearest merchant jobs.** “Add”, “People”, and “History” are vague; five equal destinations leave no place for Settings and use ambiguous text glyphs such as `♟`.
3. **Navigation is state-only, so browser/Android back behavior is not meaningful.** Refresh resets to Home and there is no predictable page history.
4. **Dashboard information is duplicated.** “Today”, “Shop Health”, and “Where is my money?” repeat sales, received money, dues, expenses, and profit, creating a long stack of cards.
5. **The primary sale workflow is amount-led ledger entry, not a clear bill workflow.** Product selection/itemization is detached in History and requires extra navigation; payment completion lacks a clear success acknowledgement.
6. **Forms have weak validation and accessibility.** Errors are page-level only, controls lack autocomplete in authentication, numeric constraints are absent, optional treatment is inconsistent, select fields can omit `name`, and values/focus are not consistently preserved after errors.
7. **Several expandable forms are long inline cards.** They push surrounding context below the fold, provide weak cancel/close affordances, and are awkward with the mobile keyboard.
8. **Data rows are clickable without semantic buttons.** Credit and history rows have no keyboard behavior or explicit action label; edit/payment intent is easy to miss.
9. **Products have an immediate consequential “Deactivate” action without an explanation or confirmation.**
10. **Loading produces layout shifts or nothing at all.** Startup uses bare text, dashboard sections appear independently, and there is no stable page-level loading treatment.
11. **Empty states are generic or grammatically generated.** “No entries found” and “No customers yet” do not explain what will appear or offer the next useful action.
12. **Malayalam-length content is unsupported.** Fixed compact rows, small captions, and crowded segment controls have not been designed for longer labels at 360px.
13. **Desktop/tablet behavior remains a narrow 560px phone column.** Larger screens do not use space to improve readability or workflow, while narrow phones still inherit multiple two-column grids.
14. **Inconsistent action hierarchy.** Neutral, primary, disclosure, and destructive actions share ad-hoc green styling; close buttons and text links vary in size and meaning.

## P2 — polish and consistency

1. Colors, spacing, radii, borders, shadows, and typography are repeated as arbitrary values across four CSS files instead of semantic tokens.
2. Dark surfaces, focus-visible states, disabled states, pressed states, and reduced-motion behavior are missing.
3. Uppercase slogans and labels add visual noise; several subtitles repeat the title’s meaning.
4. Emoji/text symbols are visually inconsistent across platforms and do not form an accessible icon system.
5. Red is used for purchases/expenses as a routine directional signal; semantic meaning relies too heavily on color.
6. Small 10–12px captions are overused and can become hard to read.
7. Horizontal chip overflow has no affordance and can conceal filters on narrow screens.
8. Missing React keys and button `type` attributes risk warnings and accidental form submission as components evolve.
9. Date/currency formatting is fixed to English rather than the selected locale.
10. Success feedback is inconsistent (“Request remembered”, a changed button label, or nothing).

## Reusable system fixes

1. Add an app preference provider with centralized translations, locale formatting, and persisted `en`/`ml` plus `system`/`light`/`dark` appearance.
2. Replace hard-coded colors with semantic CSS variables for surfaces, text, border, primary, success, warning, error, and information states.
3. Add centralized API-to-UX error mapping, typed `ApiError`, session-expiry signaling, and safe fallback copy.
4. Add shared `StatusMessage`, `EmptyState`, `Spinner`, `Dialog`, and `SubmitButton` primitives.
5. Replace the shell with a compact safe-area-aware toolbar, job-oriented navigation, and a Settings screen.
6. Standardize screen headings, action rows, mobile forms, sheets/dialogs, list rows, focus states, and 44–48px touch targets.
7. Introduce hash-backed page navigation so browser and Android back behavior follows page changes without a new routing dependency.

## Implementation order

1. Preferences/i18n and semantic theme tokens.
2. Safe API error/session layer and shared feedback/dialog primitives.
3. Compact shell, navigation, Settings, and logout confirmation.
4. Authentication and primary entry/payment workflows.
5. Dashboard density, lists, forms, empty/error/loading states, and destructive confirmation.
6. Responsive/Malayalam/dark-mode polish across all remaining screens.
7. Regression tests, viewport verification, typecheck, tests, and production build.

## Baseline viewport observations

- **320–360px:** two-column form/metric layouts become cramped; long labels and Malayalam would wrap aggressively; horizontally scrolling filters can hide choices.
- **375–430px:** the 76px header plus 72px bottom navigation leaves unnecessarily little working space; stacked dashboard sections require excessive scrolling.
- **Tablet/desktop:** the fixed 560px shell wastes space and provides no adaptive layout, though it avoids uncontrolled line lengths.

These baseline findings were recorded before implementation. Final verification records only viewports and workflows actually exercised after the changes.
