# TODO

Outstanding work from the [PRD](PRD.md) audit. Priority roughly top-to-bottom.

Legend: ⚠️ partial — ❌ missing — ✅ done (§ kept for reference)

> Audited against commit `62042fd`. Most PRD features previously listed as missing
> (§12, §13, §16, §18, §19, §22, §23, §31, organizer auto-assign, AI tools, QR
> scanning, keyboard shortcuts) are already implemented. Struck-off items are done;
> only the residual gaps below remain.

## Search

- ⚠️ **Search & Filtering (§14)** — Global search covers all PRD fields but is free-text
  only (`/api/search` has no filters). Parts page (`/api/parts`) has only `category` +
  `low_stock_only` + `unassigned_only`. Add:
  - Filter panel on Search/Parts: category, package, location, manufacturer, stock status
    (in stock / low / out / reserved), storage status, min/max quantity.
  - **LCSC-style parametric search** over `tolerance`, `voltage_rating`, `current_rating`,
    `msl`, and `other_specs` JSONB — currently not searchable anywhere.
  - Trigger/pg_trgm indexes for the leading-wildcard `ILIKE` queries.
  - Deduplicate the three near-identical part-search blocks (`api/search.py`,
    `api/parts.py`, `services/ai.py:_tool_search_parts`); `/api/parts` and the AI tool
    also omit `Part.notes` while `/api/search` includes it.

## Inventory & Locations

- ✅ **Moving Storage (§12)** — whole-location move implemented (`POST /api/locations/{id}/move`
  + `MoveLocation.tsx`). Residual:
  - `LocationMove.new_parent_id` is non-null, so a location cannot be moved to root via
    `/move`; `POST /api/locations`/`PATCH /{id}` path allows `parent_id: null` but
    `update_location` lacks the subtree-cycle guard the move endpoint has.
- ⚠️ **QR Codes (§13)** — generation, camera scanning, and all location-page actions
  (view/add/remove/move/history/view part/report discrepancy) implemented. Residual:
  - `Scan.tsx` only matches `/locations/{id}`; organizer/compartment QR payloads
    (`partsdb:organizer:{id}:compartment:{id}`) are rejected even though they are printed.
  - `GET /api/locations/by-qr/{qr_code}` is unused dead code from the frontend.

## Organizers

- ⚠️ **Organizer System (§24-31)** — greedy packer, part-driven sizing, auto-assign of
  unassigned parts into empty compartments, stackable lips, wall-mount plate, QR pocket,
  presets, and STL export all exist. Residual:
  - Optional **ESP32 mount** and **LED placement** (§29) not emitted in generated STLs.
  - QR feature is an additive raised box (no boolean subtract), not a recessed pocket.
  - `clearance`, mounting points, and label area are stored but ignored by the mesh builder.
  - Organizers page exposes no feature toggles (stackable/wall-mount/qr); flags come only
    from the preset name or an opaque `config` dict the UI never sets.
  - `auto-assign` only fills *existing* empty compartments; new-organizer proposals are
    only reachable through the AI `suggest_organization` tool.
  - Compartment labels omit quantity (`Qty: 482`); output is browser-print HTML, not PDF;
    no generic part/location shelf labels.

## AI

- ⚠️ **AI (§39-40)** — provider abstraction, streaming chat, and read-only tools
  (including `suggest_organization`) exist. Residual:
  - No write-action tools (all tools read-only; PRD allows AI to use normal APIs).
  - No dedicated "what do I need to buy to build N boards?" tool (partially covered by
    `get_project` build-qty + `match_bom_item`).
  - AI page example prompts omit an "organize my unassigned parts" example.

## UX

- ⚠️ **UX (§47)** — QR scanning, `?` help, `g l`/`g p` nav, `/` search focus, `n` new part
  exist. Residual:
  - `Ctrl+K` handler checks only `ctrlKey`, not `metaKey` (Cmd+K on macOS does nothing).
  - No keyboard shortcuts for the frequent transaction actions (add/remove stock).
  - Organizer/compartment QR codes are not scannable (see QR Codes above).

## Hardware (not required for MVP)

- ❌ **ESP32 Smart Organizers (§32-38)** — Entire feature missing: API, device registration,
  LED control, macropad input, firmware. `models/esp32.py` defines `ESP32Device` but there
  is no `api/esp32.py` and no routes. Explicitly out of MVP scope.
