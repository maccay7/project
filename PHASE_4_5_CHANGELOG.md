# Phase 1–5: Financial Pipeline Refactor Changelog

## Phase 1 — Parser Hardening (`0fcb846`)
- `isNumeric` requires the full string to be a plain number; rejects date
  separators/letters — `10/6/3261` can no longer parse as `10`.
- Tabular record loop breaks on new header blocks (≥4 recognised headers).
- Numeric-typed fields reject date-like values; rejections recorded in
  `record.warnings`.
- `pairKey` dedup: one source cell can claim only one canonical field.

## Phase 3 — Flagged Defaults (`fd86b0e`)
- `_resolve_day_count`: missing convention → Actual/360 (MM/T-Bills) or
  30/360 (Bonds), recorded in `assumptions_applied` — never silent.
- `_infer_settlement_t1`: SettlementDate = ValuationDate + 1 business day,
  Modified-Following month guard.
- `calculate_data` returns `overall_status` (complete/partial/failed) +
  `status_counts`; per-row `partial` status preserved (no blanket 422).

## Phase 4 — Financial Logic (`e4c489c`, `6eb5975`, `7698a7e`, `37ec7f1`)
- T-Bill yield gating: ≤365d → money-market yield only; >365d → BEY only
  + `classification_warning` (Note/Bond suggestion).
- `interpolate_nss_curve(term, β0..β3, τ1, τ2)` — standard NSS spot rate.
- `_nss_discount_percent`: explicit `nss_rate` → β/τ interpolation;
  `country_risk_premium` always added. NSS overrides sheet `discount_rate`
  for T-Bills, Money Market, and Bond DCF discounting.
- Detection field defs + tabular aliases for `nss_rate`, `beta0..3`,
  `tau1`, `tau2`, `country_risk_premium`.
- Verified RBZ case: 2.98% base + 7.65% CRP = 10.63% (sheet 8.94% ignored).

## Phase 2 — Cleaning Contract (`95bc232`)
- `calculateMetrics` refreshes `excludedDetectedFields` + `cleanedData`/
  `cleanedSourceData` from the saved workflow before building the payload —
  Cleaning-page unchecks/edits are honoured; excluded fields never fall back
  to auto-detected values.

## Phase 5 — UI (`cc8446d`, `211a4dd`, `0bc4dd0`)
- Dismissible `overall_status` banner (green/yellow/red + counts).
- Collapsible "Valuation Assumptions" panel (✅ applied / ⚠️ override);
  empty state message when no assumptions.
- Cleaning preview per-row Status column (✅/⚠️/❌ + message, 40-char
  truncation) with Show All/Warnings/Errors filters persisted in
  sessionStorage.

## Known Issues
- `test_persistence_routes::test_session_get_uses_actual_version_count`
  fails on clean HEAD — pre-existing, unrelated; investigate separately.
- ExcelViewer grid has no per-cell tooltip/row-tint support; validation
  messages shown in a companion column instead (documented follow-up).
