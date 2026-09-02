# PartsDB

Self-hosted electronics component inventory management for the workshop.

PartsDB replaces boxes of unorganized parts with a searchable digital inventory tied to physical
storage locations. Track exact quantities, keep an immutable audit trail, import BOMs, reserve
stock for projects, generate shopping lists, and print QR-coded organizer labels — all from a
single Docker Compose stack.

> Core functionality works fully offline. LCSC/DigiKey lookups and AI features are optional
> integrations, never dependencies.

---

## Features

- **Parts** — manufacturer, MPN, LCSC/DigiKey numbers, value, package, category, tolerance,
  voltage/current rating, MSL, specs, datasheets, notes, and attachments.
- **Inventory** — exact quantities in pieces, across hierarchical physical locations.
- **Transactions** — every quantity change is recorded as an immutable audit-log entry
  (timestamp, part, quantity, location, reason, project, reservation, source, notes).
- **Locations** — arbitrary-depth hierarchy (Rack → Bin → Compartment), QR codes, and
  move-location support that carries stock with it.
- **Low-stock thresholds** — optional min / desired / reorder quantities per part.
- **Search** — one box across part identity, values, specs, locations, projects, and BOMs.
- **Projects & BOMs** — CSV import with configurable column mapping, BOM revisions, build
  quantity, and match inventory against requirements.
- **Reservations** — reserve stock for a project without removing physical inventory.
- **Shopping lists** — auto-generate purchase requirements from missing BOM parts, low stock,
  and project needs.
- **Supplier integrations** — lookup and import parts from LCSC and DigiKey, including price,
  stock, datasheet, and specs.
- **Organizers** — generate 3D-printable storage organizer STL files and assign parts to
  compartments.
- **Attachments & backups** — store datasheets/images/CAD files, and export the full state.
- **Optional AI** — natural-language queries and BOM analysis through an OpenAI-compatible
  provider (including local models like Ollama).

---

## Tech stack

| Layer      | Technology                                   |
|------------|----------------------------------------------|
| Frontend   | React 18, TypeScript, Vite, react-router     |
| Backend    | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic |
| Database   | PostgreSQL 16                                |
| Migrations | Alembic                                      |
| Deploy     | Docker Compose (offline-friendly `--pull never`) |

---

## Quick start

Requires Docker with Compose v2.

```bash
git clone https://github.com/sneakylizard123-4/PartsDB partsdb
cd partsdb
cp .env.example .env   # optional, sensible defaults provided
./run.sh               # build & start in background
```

Then open <http://localhost:3000>.

| Component | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:3000        |
| Backend   | http://localhost:8000        |
| API docs  | http://localhost:8000/docs   |

Default login (change in `.env` before first run if exposed):

```text
username: admin
password: admin
```

### `run.sh` commands

```bash
./run.sh               # build & start in background (same as up)
./run.sh up            # build & start
./run.sh down          # stop everything
./run.sh logs          # follow container logs
./run.sh rebuild       # rebuild images and recreate containers
./run.sh status        # show container status
```

All builds use `--pull never` and only rebuild changed layers, so restarts and rebuilds work
offline once images are cached. The equivalent raw command is:

```bash
docker compose up -d --build
```

A `Makefile` with `up`, `down`, `logs`, and `rebuild` targets is also provided.

---

## Configuration

All configuration is via environment variables, either exported or in a root `.env` file.
See [`.env.example`](.env.example) for the full list with defaults.

| Variable                | Purpose                                             | Default        |
|-------------------------|-----------------------------------------------------|----------------|
| `SECRET_KEY`            | JWT signing secret — set a random value             | `dev-secret...` |
| `ADMIN_USERNAME`        | Initial admin user (created on first start)         | `admin`        |
| `ADMIN_PASSWORD`        | Initial admin password                              | `admin`        |
| `ADMIN_EMAIL`           | Initial admin email                                 | `admin@example.com` |
| `POSTGRES_USER/PASSWORD/DB` | PostgreSQL credentials                          | `partsdb`      |
| `LCSC_API_KEY`          | Optional LCSC API key (not required for public API) | *(empty)*      |
| `DIGIKEY_CLIENT_ID` / `DIGIKEY_CLIENT_SECRET` / `DIGIKEY_API_TOKEN` | DigiKey API credentials | *(empty)* |
| `AI_PROVIDER`           | `none` or an OpenAI-compatible provider             | `none`         |
| `AI_API_KEY` / `AI_BASE_URL` / `AI_MODEL` | AI provider settings                   | *(empty)*      |

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## Usage overview

The primary workflow:

```
Find part  →  know exactly where it is  →  take/use part  →  record transaction  →  accurate inventory
```

Main screens: **Dashboard**, **Parts**, **Inventory**, **Transactions**, **Locations**,
**Projects**, **Shopping List**, **Organizers**, **Supplier Import** (`/import`), and
**Settings**.

To add a part from a supplier, use the supplier import page and search an LCSC part number
(e.g. `C25804`) or a keyword — the backend fetches specs, price, stock, datasheet, and MSL.
Or create a part manually and set storage/ordering thresholds.

---

## Supplier integrations

- **LCSC** — uses LCSC's public web endpoints; works without an API key. Returns part number,
  manufacturer, MPN, description, package, price breaks, stock, datasheet, specs, and MSL.
- **DigiKey** — requires `DIGIKEY_CLIENT_ID` + a client secret or static API token.

Both degrade gracefully: if a supplier is unavailable, lookups fail with a clear message and
the rest of the app keeps working.

---

## AI (optional)

The **AI Assistant** (`/ai`) provides natural-language inventory queries and BOM analysis. It
works with any OpenAI-compatible Chat Completions API — local (Ollama) or hosted (OpenRouter,
OpenAI, Together, etc.). The LLM never accesses the database directly; it calls read-only
application tools, so it can only see what the app's own APIs expose.

With `AI_PROVIDER=none` (default) all normal functionality works unchanged; `/ai` shows a config
notice instead.

Set these in `.env`:

| Variable        | Purpose                                            | Example |
|-----------------|----------------------------------------------------|---------|
| `AI_PROVIDER`   | `none` for off, or the provider `chat/completions` base URL | `http://host.docker.internal:11434/v1` (Ollama) or `https://openrouter.ai/api/v1` |
| `AI_API_KEY`    | Provider API key (Ollama may ignore)               | `sk-...` |
| `AI_MODEL`      | Model name to use                                   | `qwen2.5:7b` or `openai/gpt-4o-mini` |

Example with a local [Ollama](https://ollama.com) instance (free, no key):

```dotenv
AI_PROVIDER=http://host.docker.internal:11434/v1
AI_MODEL=qwen2.5:7b
```

> Note: the backend runs inside Docker, so use `host.docker.internal` to reach a service on your
> host machine. The AI feature and all prompts are optional — they never block core inventory use.

---

## Development

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload          # http://localhost:8000
ruff check .                            # lint
alembic upgrade head                    # apply migrations
```

### Frontend

```bash
cd frontend
npm install
npm run dev                             # http://localhost:5173 (proxies /api to :8010, or set VITE_API_PROXY)
npm run build                           # typecheck + production build
```

Migrations live in `backend/alembic/versions/` and are applied automatically on container
startup (`alembic upgrade head`).

---

## API

REST API at `/api`, auto-documented at <http://localhost:8000/docs> (Swagger UI). Endpoints
cover: auth, account, parts, locations, inventory, transactions, search, dashboard, projects,
BOMs, reservations, shopping lists, suppliers, organizers, attachments, and backup.

## Project structure

```text
backend/
  app/
    api/        # FastAPI route modules
    models/     # SQLAlchemy models
    services/   # business logic, supplier catalog, organizer STL, etc.
    schemas.py  # Pydantic schemas
  alembic/      # database migrations
frontend/
  src/
    pages/      # route screens
    components/ # shared UI
    api.ts      # API client
    types.ts    # shared TypeScript types
docker-compose.yml
run.sh
Makefile
```
