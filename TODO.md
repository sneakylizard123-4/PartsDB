# TODO

Outstanding work from the [PRD](PRD.md) audit. Priority roughly top-to-bottom.

Legend: ⚠️ partial — ❌ missing

## Inventory & Locations

- ⚠️ **Moving Storage (§12)** — Per-part moves exist, but there is no whole-location move that automatically carries all inventory to a new parent.
- ⚠️ **QR Codes (§13)** — Generation works. Missing: camera/QR scanning, and the location-page actions "move location" and "report discrepancy" wired to QR.

## BOMs & Projects

- ⚠️ **BOM Matching UI (§16)** — Exact matching works. No UI for reviewing/approving compatible substitutions (the "[Accept substitute]" flow).
- ⚠️ **BOM Revisions (§18)** — Build-quantity multiplication works. Missing revision diffing (V1→V2 comparison showing +/−/~ changes and inventory impact).

## Planning

- ⚠️ **Shopping List statuses (§19)** — Generation works. Missing split by available / reserved / missing / recommended-purchase-quantity.
- ❌ **Supplier Comparison (§22)** — No price/stock comparison across LCSC vs DigiKey with a recommendation.
- ⚠️ **Dashboard (§23)** — Most widgets present. Missing BOM drilldown and a few PRD stat items (empty storage, recent reservations).

## Organizers

- ⚠️ **Organizer System (§24-30)** — Greedy packer exists. Missing: part-driven compartment sizing, automatic unassigned-part assignment, and physical features (stackability, wall mount, QR, ESP32 mount) in generated STLs.
- ❌ **Labels (§31)** — No compartment label generation (part info + QR) for printing.

## AI

- ⚠️ **AI (§39-40)** — Provider abstraction + read-only inventory tools exist. Missing: organization-tooling support (e.g. "organize my unassigned parts") and any of the optional AI features not yet wired.

## UX

- ⚠️ **UX (§47)** — Missing QR scanning and minimal keyboard shortcuts for workshop use.

## Hardware (not required for MVP)

- ❌ **ESP32 Smart Organizers (§32-38)** — Entire feature missing: API, device registration, LED control, macropad input, firmware. Explicitly out of MVP scope.
