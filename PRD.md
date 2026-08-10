# PartsDB — Product Requirements Document

## 1. Overview

PartsDB is a self-hosted, single-user electronics component inventory management application.

The primary purpose is to replace physical boxes of unorganized electronics parts with a searchable digital inventory tied to physical storage locations.

The application should manage:

* Electronic components
* Screws and mechanical hardware
* Physical storage locations
* Exact inventory quantities
* BOMs
* Projects
* Inventory reservations
* Purchasing requirements
* Supplier information
* Part substitutions
* QR-coded physical storage
* 3D-printable storage organizers
* Optional ESP32-enabled physical organizers
* Optional AI-assisted workflows

The web application is the primary product.

ESP32 hardware is entirely optional and must never be required for the application to function.

---

# 2. Core Principles

### Self-hosted

The application must be designed to run entirely on the user's own server.

The deployment should require a single command, preferably:

```bash
docker compose up -d
```

The application should not require an external SaaS service.

External services such as LCSC, DigiKey, and AI providers are integrations rather than application dependencies.

### Single user

Version 1 is single-user.

Do not build a multi-user permission system yet.

The architecture should not prevent adding multi-user support later.

### Offline-capable local inventory

Core inventory functionality must continue working when external services such as LCSC, DigiKey, or AI APIs are unavailable.

Internet access should only be required for external integrations.

### API-first

All important application functionality should be accessible through an API.

The React frontend should use the same API that external clients, scripts, and future ESP32 hardware use.

---

# 3. Recommended Technology Stack

Use:

### Frontend

* React
* TypeScript
* Vite
* Modern component library of choice
* Responsive desktop-first UI

### Backend

Use a typed REST API.

Preferred:

* Python
* FastAPI
* SQLAlchemy
* Pydantic

Alternative backend technologies are acceptable if there is a strong reason.

### Database

PostgreSQL.

Do not use SQLite for the main deployment unless there is a compelling technical reason.

### Deployment

Docker Compose.

Initial services:

```text
frontend
backend
postgres
```

Additional workers/services can be added later if needed.

The application should have sensible environment-variable configuration.

---

# 4. Parts

A part represents a logical component type, not a physical container.

Example:

```text
Internal ID:
RES-0603-10K

Value:
10kΩ

Package:
0603

Tolerance:
±1%

Manufacturer:
Yageo

MPN:
RC0603FR-0710KL

LCSC:
C25804

DigiKey:
311-10.0KHRCT-ND
```

All identification fields should be optional.

Supported fields should include:

* Internal part ID
* Manufacturer
* Manufacturer part number
* LCSC part number
* DigiKey part number
* Value
* Package
* Description
* Category
* Tolerance
* Voltage rating
* Current rating
* Other specifications
* Datasheet
* Notes
* Images
* Attachments

The schema should be extensible for additional specifications.

---

# 5. Units

Version 1 inventory quantities are always measured in pieces.

Examples:

```text
482 × resistors
127 × screws
50 × ICs
```

Do not implement arbitrary units such as meters or grams in v1.

---

# 6. Inventory

Inventory represents physical stock of a part.

A part may exist in multiple physical locations.

Example:

```text
10kΩ 0603

Rack 1 / Bin 4 / A5:
482 pieces

Desk Organizer / B3:
37 pieces
```

The system must maintain exact quantities.

---

# 7. Inventory Transactions

Every inventory quantity change must create an immutable transaction record.

Examples:

```text
+500 pieces
-12 pieces
+37 pieces
```

Transactions should contain:

* Timestamp
* Part
* Quantity change
* Location
* Reason
* Related project, if applicable
* Related reservation, if applicable
* Source
* Notes

Example:

```text
2026-08-09 15:32

10kΩ 0603
-12 pieces
Rack 1 / Bin 4 / A5
Reason: project usage
Project: Mesh Node V2
```

The audit log must not be editable through the normal UI.

---

# 8. Minimum Stock

Each part may optionally define:

* Minimum quantity
* Desired quantity
* Reorder quantity

Example:

```text
Current: 82
Minimum: 50
Desired: 500
```

When inventory drops below the minimum, the part should be marked as low stock.

The application should be able to automatically add low-stock parts to a shopping list.

---

# 9. Reservations

Inventory can be reserved for projects.

Example:

```text
Physical:
500

Reserved:
200

Available:
300
```

Reservations must reduce available inventory but must not remove physical inventory.

Reserved stock should be visually distinguished throughout the application.

A physical organizer may optionally display a different LED behavior for reserved stock.

---

# 10. Locations

Physical storage must be modeled hierarchically.

Example:

```text
Rack 1
└── Bin 4
    ├── A1
    ├── A2
    ├── A3
    └── A5
```

A location should have:

* Name
* Parent location
* Type
* Dimensions
* Notes
* QR code
* Optional organizer association

The hierarchy should support arbitrary depth even if the default UI uses:

```text
Rack → Bin → Compartment
```

---

# 11. Compartments

A compartment is the final physical storage location for a part.

Version 1 rule:

**One part type per compartment.**

A compartment may contain multiple physical containers/lots of the same part if necessary, but different part types should not share a compartment.

Empty compartments should be represented in the database.

This allows the application to identify unused physical storage.

---

# 12. Moving Storage

Moving a physical container or location should automatically move the associated inventory.

Example:

```text
Rack 1 / Bin 4 / A5

        ↓ move

Rack 2 / Bin 1 / B3
```

The system should not require manually editing every part stored there.

---

# 13. QR Codes

QR codes should identify physical containers/locations rather than permanently identifying a part.

Example:

```text
Rack 1 / Bin 4 / A5
```

Scanning the QR code should open the corresponding location in the web application.

The contents of the location may change without needing to replace the QR code.

The location page should provide actions such as:

* View contents
* Add stock
* Remove stock
* Move location
* View transaction history
* View part
* Report discrepancy

---

# 14. Search

Global search must search across:

* Internal part ID
* Manufacturer
* MPN
* LCSC SKU
* DigiKey SKU
* Value
* Package
* Description
* Category
* Location
* Project
* BOM
* Notes

Searching for a location such as `A5` should be able to locate the physical compartment.

Search should be fast enough for normal workshop use.

---

# 15. BOM Import

Version 1 BOM input is CSV.

Do not implement direct `.kicad_sch` parsing initially.

The CSV importer must have configurable column mapping.

Example:

```text
Reference → Designator
Value → Value
Footprint → Footprint
MPN → Manufacturer Part Number
```

The importer should allow users to map arbitrary CSV columns to supported BOM fields.

The system should preview the imported BOM before committing it.

---

# 16. BOM Matching

The system should match BOM requirements against inventory.

Matching levels:

### Exact

Manufacturer part number matches.

### Strong

Manufacturer, package, value, tolerance, and relevant specifications match.

### Compatible

Electrical and physical specifications indicate that the existing part can substitute for the requested part.

### Manual

User explicitly approves the match.

The UI should show the confidence/matching reason.

Example:

```text
R1-R20

Required:
20 × 10kΩ 0603 ±1%

Inventory:
15 × exact match
5 × compatible substitute

[Accept substitute]
```

The system must not silently consume questionable substitutions.

---

# 17. Projects

A project should contain:

* Name
* Description
* BOM
* BOM revisions
* Build quantity
* Inventory reservations
* Missing parts
* Purchased parts
* Substitutions
* Attachments
* Notes
* Status

Build quantity must multiply BOM requirements.

Example:

```text
BOM:
10 × 100nF

Build quantity:
5

Required:
50 × 100nF
```

---

# 18. BOM Revisions

Projects must support BOM revisions.

When a new BOM is uploaded, the system should compare it against the previous revision.

Example:

```text
V1 → V2

+ C17 100nF
- R12 4.7k
~ U3 MPN changed
```

The system should calculate inventory impact.

---

# 19. Shopping Lists

The application should generate shopping requirements based on:

* Missing BOM components
* Insufficient inventory
* Low-stock parts
* Project requirements

Example:

```text
Shopping List

STM32H743VIT6       3
10kΩ 0603           418
100nF 0603          250
M3×8 screw          40
```

Shopping lists should distinguish:

* Already available
* Reserved
* Missing
* Recommended purchase quantity

---

# 20. LCSC Integration

Integrate LCSC as an external supplier.

The application should retrieve, where available:

* Part number
* Manufacturer
* MPN
* Description
* Package
* Datasheet
* Stock
* Pricing
* Price breaks
* Supplier SKU
* Relevant specifications

The integration must fail gracefully if LCSC is unavailable.

---

# 21. DigiKey Integration

Integrate DigiKey similarly.

The architecture should make supplier integrations modular.

Do not tightly couple the inventory system to either supplier.

A generic supplier interface should be used where practical.

---

# 22. Supplier Selection

When a part needs to be purchased, the application should be able to compare supplier options.

Example:

```text
10kΩ 0603 ±1%

LCSC:
500 available
$0.006 each

DigiKey:
12000 available
$0.011 each
```

The system should be able to recommend an option based on price, stock, and quantity.

---

# 23. Dashboard

The dashboard should show:

* Total parts
* Low-stock parts
* Missing BOM components
* Current projects
* Shopping requirements
* Recent inventory activity
* Unassigned parts
* Empty storage
* Recent reservations

Primary actions:

```text
Import BOM
Add Part
Find Part
Add Inventory
Shopping List
Generate Organizer
```

---

# 24. Physical Organizer System

PartsDB should contain its own organizer-generation system.

The system will initially use a custom organizer ecosystem rather than Gridfinity or another external standard.

Organizers should be stackable and/or wall-mounted.

The physical system must remain usable without electronics.

---

# 25. Organizer Presets

Provide predefined organizer presets for common use cases:

* Small SMD parts
* Large SMD parts
* ICs
* Screws
* Mixed components
* Stackable bins
* Wall-mounted bins

Users must also be able to create custom organizer configurations.

---

# 26. Organizer Generator

The generator accepts constraints such as:

```text
Maximum width: 100 mm
Maximum depth: 100 mm
Maximum height: 10 mm

Required compartments:
20
```

Other configurable parameters:

* Outer width
* Outer depth
* Outer height
* Number of compartments
* Minimum compartment size
* Divider thickness
* Wall thickness
* Clearance
* Label area
* Mounting points
* Stackability
* Wall-mounting configuration

The generator should optimize the internal layout while respecting the user's constraints.

---

# 27. Variable Compartment Sizes

Compartments do not need to be uniform.

The optimizer may produce layouts such as:

```text
┌────┬────┬────────────┐
│ R1 │ R2 │            │
├────┼────┤    ICs     │
│ R3 │ R4 │            │
├────┴────┼────────────┤
│ Screws  │ Capacitors │
└─────────┴────────────┘
```

The system should consider the physical requirements of the assigned parts.

For example, a tiny 0603 resistor should not automatically receive the same compartment size as a bag of M3 screws.

---

# 28. Organizer Assignment

Parts should have storage status:

```text
Unassigned
Assigned
Printed
Installed
```

The system should identify parts that have no physical storage.

Example:

```text
42 parts have nowhere to live.

[Generate Organizer]
```

The organizer generator should be able to automatically assign unassigned parts to generated compartments.

The user must be able to review and modify the proposed assignment before generation.

---

# 29. Organizer Output

Version 1 should generate:

* STL

Future formats may include 3MF, but STL is the only required output for v1.

The generated organizer should include appropriate physical features for:

* Label placement
* QR identification
* Optional ESP32 mounting
* Optional LED placement
* Stackability
* Wall mounting

---

# 30. Generic FDM

The organizer generator must target generic FDM printing.

Do not hard-code requirements for a specific printer.

The generated geometry should use practical FDM-friendly wall thicknesses and clearances.

Printer-specific profiles can be added later.

---

# 31. Labels

Each physical compartment should be able to receive a generated label.

Example:

```text
10kΩ
0603
±1%

Qty: 482

[QR]
```

Labels should include enough information to identify the part without opening the web application.

---

# 32. ESP32 Smart Organizers

ESP32 hardware is optional.

A large organizer may contain one ESP32.

Example:

```text
Large Organizer
├── ESP32
├── LED A1
├── LED A2
├── LED A3
├── ...
└── Macropad
```

The ESP32 communicates with the server over Wi-Fi.

---

# 33. Smart Organizer LEDs

Each compartment may have an LED.

When a part needs to be located, the corresponding LED should blink.

Example:

```text
Search:
10kΩ 0603

Rack 1 / Bin 4 / A5

A5 LED:
BLINK
```

LED behavior should be configurable later.

---

# 34. Smart Organizer Macropad

Large organizers may include a custom physical macropad.

The macropad should allow physical inventory actions.

Example:

```text
[ A1 ] [ A2 ] [ A3 ] [ A4 ]
[ B1 ] [ B2 ] [ B3 ] [ B4 ]
[ +  ] [ -  ] [ OK ]
```

The exact keypad design is flexible.

The physical interface should ultimately be able to trigger API operations such as:

* Add inventory
* Remove inventory
* Select compartment
* Confirm transaction
* Find part

---

# 35. ESP32 Architecture

ESP32 devices should be thin clients.

They should not maintain the authoritative inventory database.

The server remains authoritative.

The ESP32 should:

* Connect to Wi-Fi
* Authenticate with the server
* Report button/macropad events
* Receive LED commands
* Report device status

The server determines inventory state and desired LED behavior.

---

# 36. ESP32 API

The API should be generic enough for future hardware.

Conceptually:

```http
GET /api/organizers/{id}/state

POST /api/organizers/{id}/input
```

The exact API design is up to implementation.

The API should support:

* Device registration
* Device authentication
* Device state
* LED commands
* Input events
* Heartbeat/status
* Firmware version

---

# 37. ESP32 Failure Behavior

If the server or Wi-Fi is unavailable:

* The ESP32 may remain idle.
* It must not become the authoritative inventory database.
* Local inventory should not be modified permanently without server confirmation.

The web application must remain fully usable without ESP32 devices.

---

# 38. Power

Smart organizers use 5V wired power.

The organizer electronics should be designed around a common 5V supply.

Do not require individual batteries for organizers.

---

# 39. AI

AI is optional.

The application must function normally with AI disabled.

The AI integration should use an abstraction layer so providers can be changed.

Potential providers:

* Hack Club AI
* OpenAI-compatible APIs
* Local models through Ollama
* Other compatible providers

The exact provider must not be hard-coded into core application logic.

---

# 40. AI Features

Potential AI features include:

### Natural language inventory queries

```text
Do I have enough 10k resistors to build five Mesh Node V2 boards?
```

### BOM analysis

```text
What parts am I missing?
```

### Part matching

```text
Can this resistor substitute for the BOM resistor?
```

### Purchasing

```text
What should I buy from LCSC?
```

### Storage organization

```text
Organize my unassigned parts.
```

### Project analysis

```text
What do I need to buy to build three boards?
```

AI should use normal application APIs and permissions.

AI must not directly bypass inventory transaction logic.

---

# 41. Attachments

Parts and projects should support attachments such as:

* Datasheets
* Images
* Notes
* CAD files
* KiCad files
* Other documents

The application should store attachment metadata in the database and files in appropriate persistent storage.

---

# 42. Backup

Provide one-click export of the complete application state.

The backup should include:

* Parts
* Inventory
* Locations
* Transactions
* Projects
* BOMs
* Reservations
* Shopping lists
* Organizer configurations
* Supplier data
* Settings

A portable JSON/database backup format should be preferred.

Attachments should also be included in a complete backup.

---

# 43. Security

The application is single-user but self-hosted.

Implement basic authentication.

API keys should be supported for future ESP32 devices.

Secrets such as supplier API credentials and AI API keys must be stored through environment variables or secure application configuration, not hard-coded.

---

# 44. Data Model

The initial schema should include at minimum:

```text
Part
Supplier
SupplierPart
InventoryLocation
InventoryItem
InventoryTransaction
Project
BOM
BOMRevision
BOMItem
Reservation
ShoppingList
ShoppingListItem
Organizer
OrganizerCompartment
ESP32Device
Attachment
```

Relationships should allow:

```text
Part
 ├── SupplierPart
 ├── InventoryItem
 ├── BOMItem
 └── Attachment

InventoryLocation
 ├── child locations
 ├── InventoryItem
 └── OrganizerCompartment

Project
 ├── BOM
 ├── BOMRevision
 ├── Reservation
 └── Attachment
```

The exact schema should be refined during implementation.

---

# 45. API Requirements

The backend API should expose resources for:

```text
/parts
/inventory
/locations
/transactions
/projects
/boms
/reservations
/shopping-lists
/suppliers
/organizers
/esp32
/attachments
/search
```

API documentation should be automatically generated where possible.

---

# 46. Frontend Requirements

The React application should contain at least:

```text
Dashboard
Parts
Inventory
Locations
Projects
BOMs
Shopping List
Organizers
Transactions
Settings
```

Part pages should show:

* Identity
* Specifications
* Inventory
* Locations
* Reservations
* Supplier information
* BOM usage
* Transaction history
* Attachments

---

# 47. UX Requirements

The application is intended to be used while physically working in a workshop.

Prioritize:

* Fast search
* Large actionable buttons
* Minimal navigation
* Clear stock status
* Clear physical location
* QR scanning
* Keyboard shortcuts
* Responsive layout
* Low-friction inventory transactions

A user should be able to answer:

> "Where are my 10k resistors?"

within a few seconds.

---

# 48. Initial Implementation Order

Implement incrementally.

### Phase 1 — Foundation

* Repository setup
* Docker Compose
* PostgreSQL
* Backend
* React frontend
* Database migrations
* Authentication
* API structure

### Phase 2 — Inventory

* Parts
* Locations
* Inventory
* Exact quantities
* Transactions
* Search
* Low-stock thresholds

### Phase 3 — Physical organization

* Hierarchical locations
* QR codes
* Compartment management
* Empty compartments
* Move locations
* Labels

### Phase 4 — BOMs

* CSV import
* Column mapping
* BOM preview
* BOM matching
* Compatible parts
* Projects
* BOM revisions

### Phase 5 — Planning

* Reservations
* Missing parts
* Shopping lists
* Supplier integrations
* LCSC
* DigiKey

### Phase 6 — Organizers

* Organizer database model
* Presets
* Custom dimensions
* Layout optimizer
* Part assignment
* STL generation
* Labels
* QR integration

### Phase 7 — AI

* Provider abstraction
* Hack Club AI integration
* Natural-language inventory queries
* BOM analysis
* Part matching assistance
* Purchasing assistance

### Phase 8 — Hardware

* ESP32 API
* Device registration
* Wi-Fi protocol
* LED control
* Macropad input
* ESP32 firmware
* Organizer electronics

---

# 49. Non-Goals for Version 1

Do not initially implement:

* Direct KiCad schematic parsing
* Multi-user accounts
* Complex role/permission systems
* Gridfinity compatibility
* Mobile-native applications
* Battery-powered organizers
* ESP32-local inventory databases
* Arbitrary physical measurement units
* Advanced warehouse management
* Automatic purchasing/payment
* Fully autonomous AI inventory modification

These can be added later.

---

# 50. Definition of Done for MVP

The MVP should allow the user to:

1. Start the entire application with Docker Compose.
2. Create parts.
3. Define physical racks, bins, and compartments.
4. Add exact quantities of parts.
5. Move parts between locations.
6. Record every inventory transaction.
7. Search for a part and immediately see its physical location.
8. Generate and scan QR codes for locations.
9. Import a CSV BOM.
10. Determine which BOM parts are available.
11. Reserve inventory for a project.
12. Identify missing parts.
13. Generate a shopping list.
14. Set minimum stock levels.
15. Identify unassigned parts.
16. Create an organizer configuration.
17. Generate an STL organizer within specified dimensions.
18. Assign parts to organizer compartments.
19. Export a backup of the complete inventory.

ESP32 functionality is **not required for MVP completion**.

---

# 51. Design Philosophy

PartsDB should feel like a practical workshop tool rather than an enterprise inventory system.

Avoid unnecessary complexity.

The primary workflow should be:

```text
Find part
    ↓
Know exactly where it is
    ↓
Take/use part
    ↓
Record transaction
    ↓
Inventory stays accurate
```

For projects:

```text
Import BOM
    ↓
Match inventory
    ↓
Reserve available parts
    ↓
Identify missing parts
    ↓
Generate shopping list
    ↓
Build project
```

For physical organization:

```text
Unassigned parts
    ↓
Generate organizer
    ↓
Print organizer
    ↓
Assign compartments
    ↓
Print labels/QR codes
    ↓
Install parts
    ↓
Optional ESP32 hardware
```

The system should be useful with nothing more than a browser and a printer, while leaving room for a much more elaborate physical smart-organizer ecosystem later.
