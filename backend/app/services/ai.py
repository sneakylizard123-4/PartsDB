"""AI provider abstraction and tool-calling chat loop.

Supports any OpenAI-compatible chat completions API (e.g. Ollama, OpenRouter,
OpenAI, Together, etc.). The LLM never touches the DB directly — it calls
application tools instead.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.bom import BOM, BOMItem
from app.models.inventory import InventoryItem
from app.models.location import InventoryLocation
from app.models.organizer import Organizer
from app.models.part import Part
from app.models.project import Project
from app.models.reservation import Reservation
from app.services.bom_matching import match_bom_item
from app.services.organizer_layout import CompartmentSpec, pack_compartments, size_for_part
from app.services.queries import part_stats, enrich_part, load_part

log = logging.getLogger(__name__)

TIMEOUT = 60.0


class AIError(Exception):
    """Raised when the AI provider cannot be reached or fails."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message = message
        self.status = status

SYSTEM_PROMPT = """\
You are PartsDB, an electronics workshop inventory assistant. \
You have read-only access to the user's component inventory database \
via the tools provided. Use them to answer questions accurately — \
always cite specific part names, quantities, locations, and suppliers. \
If you don't know or the data is insufficient, say so rather than guessing. \
Be concise and practical. When listing parts, format them clearly."""


# ── Tool definitions (OpenAI function-calling format) ──────────────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_parts",
            "description": "Search the parts inventory by keyword (value, MPN, LCSC number, description, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_part_details",
            "description": "Get full details for a specific part by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_id": {
                        "type": "string",
                        "description": "The part UUID",
                    }
                },
                "required": ["part_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_low_stock",
            "description": "List all parts that are below their minimum stock threshold.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_unassigned",
            "description": "List all parts that have no physical storage location assigned.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Get the current stock levels and locations for a specific part.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_id": {
                        "type": "string",
                        "description": "The part UUID",
                    }
                },
                "required": ["part_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_locations",
            "description": "List all storage locations (racks, bins, compartments).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "List all projects.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_project",
            "description": "Get details for a specific project including its BOM and reservations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The project UUID",
                    }
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_purchase",
            "description": "List parts that need reordering, with supplier info and suggested quantities.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_inventory",
            "description": "Return a summary count of all parts, total stock, and key stats.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_organization",
            "description": "Suggest where unassigned parts could be organized into existing or newly created organizers. Returns a read-only plan — nothing is modified.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ── Tool execution ────────────────────────────────────────────────────────────

def _tool_search_parts(db: Session, args: dict) -> str:
    term = args["query"].strip()
    like = f"%{term}%"
    from sqlalchemy import or_

    parts = (
        db.query(Part)
        .filter(
            or_(
                Part.internal_id.ilike(like),
                Part.manufacturer.ilike(like),
                Part.mpn.ilike(like),
                Part.lcsc_number.ilike(like),
                Part.digikey_number.ilike(like),
                Part.value.ilike(like),
                Part.package.ilike(like),
                Part.category.ilike(like),
                Part.description.ilike(like),
            )
        )
        .limit(10)
        .all()
    )
    if not parts:
        return f"No parts found matching '{term}'."
    results = []
    for p in parts:
        stats = part_stats(db, p)
        results.append(
            f"- {p.internal_id or p.value or p.mpn}: "
            f"{p.value or ''} {p.package or ''} {p.tolerance or ''} "
            f"by {p.manufacturer or '?'} (MPN: {p.mpn or '?'}, "
            f"LCSC: {p.lcsc_number or '?'}) — "
            f"stock: {stats['total_quantity']} pcs "
            f"({'LOW' if stats['low_stock'] else 'OK'})"
        )
    return f"Found {len(parts)} parts:\n" + "\n".join(results)


def _tool_get_part_details(db: Session, args: dict) -> str:
    part = load_part(db, args["part_id"])
    if not part:
        return "Part not found."
    data = enrich_part(db, part)
    lines = [
        f"Part: {data.get('internal_id') or data.get('value') or data.get('mpn')}",
        f"Value: {data.get('value') or '—'}",
        f"Package: {data.get('package') or '—'}",
        f"Tolerance: {data.get('tolerance') or '—'}",
        f"Voltage: {data.get('voltage_rating') or '—'}",
        f"Current: {data.get('current_rating') or '—'}",
        f"MSL: {data.get('msl') or '—'}",
        f"Manufacturer: {data.get('manufacturer') or '—'}",
        f"MPN: {data.get('mpn') or '—'}",
        f"LCSC: {data.get('lcsc_number') or '—'}",
        f"DigiKey: {data.get('digikey_number') or '—'}",
        f"Category: {data.get('category') or '—'}",
        f"Description: {data.get('description') or '—'}",
        f"Stock: {data['total_quantity']} total, {data['available_quantity']} available, {data['reserved_quantity']} reserved",
    ]
    if data["low_stock"]:
        lines.append(f"⚠ LOW STOCK (min: {part.min_qty}, desired: {part.desired_qty})")
    for loc in data.get("locations", []):
        lines.append(f"  Location: {loc['path']} — {loc['quantity']} pcs")
    if data.get("supplier_parts"):
        lines.append("Suppliers:")
        for sp in data["supplier_parts"]:
            lines.append(
                f"  {sp.get('supplier_name') or '?'}: {sp.get('supplier_sku') or '?'} "
                f"— ${sp.get('price') or '?'} (stock: {sp.get('stock')})"
            )
    return "\n".join(lines)


def _tool_list_low_stock(db: Session, args: dict) -> str:
    parts = db.query(Part).filter(Part.min_qty.isnot(None)).all()
    low = []
    for p in parts:
        stats = part_stats(db, p)
        if stats["total_quantity"] < p.min_qty:
            low.append(
                f"- {p.internal_id or p.value or p.mpn}: "
                f"{stats['total_quantity']}/{p.min_qty} pcs "
                f"(desired: {p.desired_qty})"
            )
    if not low:
        return "No parts are below their minimum stock level."
    return f"{len(low)} parts are low on stock:\n" + "\n".join(low)


def _tool_list_unassigned(db: Session, args: dict) -> str:
    parts = db.query(Part).filter(Part.storage_status == "unassigned").all()
    if not parts:
        return "All parts have assigned storage."
    items = [
        f"- {p.internal_id or p.value or p.mpn} ({p.value or ''} {p.package or ''})"
        for p in parts
    ]
    return f"{len(parts)} parts without assigned storage:\n" + "\n".join(items[:20])


def _tool_get_inventory(db: Session, args: dict) -> str:
    part = load_part(db, args["part_id"])
    if not part:
        return "Part not found."
    stats = part_stats(db, part)
    lines = [
        f"Part: {part.internal_id or part.value or part.mpn}",
        f"Total: {stats['total_quantity']} pcs",
        f"Available: {stats['available_quantity']} pcs",
        f"Reserved: {stats['reserved_quantity']} pcs",
    ]
    for loc in stats["locations"]:
        lines.append(f"  {loc['path']}: {loc['quantity']} pcs")
    return "\n".join(lines)


def _tool_list_locations(db: Session, args: dict) -> str:
    locs = db.query(InventoryLocation).all()
    if not locs:
        return "No locations defined."
    items = []
    for loc in locs:
        qty = sum(i.quantity for i in loc.inventory_items)
        items.append(f"- {loc.full_path()} ({loc.location_type or '—'}) — {qty} pcs total")
    return f"{len(locs)} locations:\n" + "\n".join(items)


def _tool_list_projects(db: Session, args: dict) -> str:
    projects = db.query(Project).all()
    if not projects:
        return "No projects."
    items = []
    for p in projects:
        bom_count = len(p.boms[0].items) if p.boms else 0
        res_count = db.query(Reservation).filter(
            Reservation.project_id == p.id, Reservation.status == "active"
        ).count()
        items.append(f"- {p.name} (id: {p.id[:8]}…) — BOM items: {bom_count}, active reservations: {res_count}")
    return f"{len(projects)} projects:\n" + "\n".join(items)


def _tool_get_project(db: Session, args: dict) -> str:
    project = db.query(Project).filter(Project.id == args["project_id"]).first()
    if not project:
        return "Project not found."
    lines = [
        f"Project: {project.name}",
        f"Description: {project.description or '—'}",
        f"Status: {project.status}",
    ]
    if project.boms:
        bom = project.boms[-1]
        lines.append(f"\nBOM ({bom.name}, {len(bom.items)} items):")
        for item in bom.items:
            candidates = match_bom_item(db, item)
            best = candidates[0] if candidates else None
            lines.append(
                f"  {item.reference}: {item.value or '?'} {item.footprint or ''} "
                f"×{item.quantity} (need: {item.quantity * (project.build_quantity or 1)}) "
                f"→ {'matched: ' + best['reason'] if best else 'NO MATCH'}"
            )
    reservations = (
        db.query(Reservation)
        .filter(Reservation.project_id == project.id, Reservation.status == "active")
        .all()
    )
    if reservations:
        lines.append(f"\nActive reservations: {len(reservations)}")
        for r in reservations:
            p = db.get(Part, r.part_id)
            lines.append(f"  {p.internal_id or p.value or p.mpn}: {r.quantity} pcs")
    return "\n".join(lines)


def _tool_suggest_purchase(db: Session, args: dict) -> str:
    parts = db.query(Part).filter(Part.min_qty.isnot(None)).all()
    suggestions = []
    for p in parts:
        stats = part_stats(db, p)
        if stats["total_quantity"] < p.min_qty:
            qty = (p.desired_qty or p.min_qty * 5) - stats["total_quantity"]
            supplier_info = ""
            if p.supplier_parts:
                sp = p.supplier_parts[0]
                supplier_info = (
                    f" — {sp.supplier.name if sp.supplier else '?'}: "
                    f"${sp.price} (stock: {sp.stock})"
                )
            suggestions.append(
                f"- {p.internal_id or p.value or p.mpn}: "
                f"buy {qty} pcs{supplier_info}"
            )
    if not suggestions:
        return "Nothing needs reordering."
    return f"Suggested purchases ({len(suggestions)} parts):\n" + "\n".join(suggestions)


def _tool_count_inventory(db: Session, args: dict) -> str:
    from sqlalchemy import func

    part_count = db.query(func.count(Part.id)).scalar() or 0
    stock = db.query(func.coalesce(func.sum(InventoryItem.quantity), 0)).scalar()
    loc_count = db.query(func.count(InventoryLocation.id)).scalar() or 0
    unassigned = db.query(func.count(Part.id)).filter(Part.storage_status == "unassigned").scalar() or 0
    return (
        f"Inventory summary:\n"
        f"  Parts: {part_count}\n"
        f"  Total stock: {stock} pcs\n"
        f"  Locations: {loc_count}\n"
        f"  Unassigned parts: {unassigned}"
    )


_ORGANIZER_PRESETS = {
    "small-smd": {
        "name": "Small SMD",
        "outer_width": 100,
        "outer_depth": 80,
        "outer_height": 12,
        "default_size": 12,
        "wall_thickness": 1.2,
        "divider_thickness": 1.2,
    },
    "large-smd": {
        "name": "Large SMD",
        "outer_width": 120,
        "outer_depth": 90,
        "outer_height": 16,
        "default_size": 20,
        "wall_thickness": 1.2,
        "divider_thickness": 1.2,
    },
    "ics": {
        "name": "ICs",
        "outer_width": 120,
        "outer_depth": 100,
        "outer_height": 18,
        "default_size": 30,
        "wall_thickness": 1.4,
        "divider_thickness": 1.4,
    },
    "screws": {
        "name": "Screws",
        "outer_width": 140,
        "outer_depth": 110,
        "outer_height": 25,
        "default_size": 35,
        "wall_thickness": 1.6,
        "divider_thickness": 1.6,
    },
    "mixed": {
        "name": "Mixed",
        "outer_width": 120,
        "outer_depth": 100,
        "outer_height": 15,
        "default_size": 20,
        "wall_thickness": 1.2,
        "divider_thickness": 1.2,
    },
    "stackable-bin": {
        "name": "Stackable Bin",
        "outer_width": 160,
        "outer_depth": 120,
        "outer_height": 30,
        "default_size": 30,
        "wall_thickness": 1.6,
        "divider_thickness": 1.6,
    },
    "wall-mounted": {
        "name": "Wall-Mounted",
        "outer_width": 160,
        "outer_depth": 60,
        "outer_height": 25,
        "default_size": 25,
        "wall_thickness": 1.6,
        "divider_thickness": 1.6,
    },
}

_PRESET_ORDER = sorted(
    _ORGANIZER_PRESETS, key=lambda k: (_ORGANIZER_PRESETS[k]["default_size"], k)
)

_MAX_PLAN_LINES = 8


def _organizer_preset_capacity(preset: dict) -> tuple[float, float, float]:
    return (
        preset["outer_width"] - 2 * preset["wall_thickness"],
        preset["outer_depth"] - 2 * preset["wall_thickness"],
        preset["outer_height"] - 3.0,
    )


def _part_label(part) -> str:
    return part.internal_id or part.value or part.mpn or getattr(part, "id", "?")


def _compartment_label(comp) -> str:
    return comp.label or f"R{comp.row + 1}C{comp.col + 1}"


def _format_part(part, size) -> str:
    w, d, h = size
    return (
        f"{_part_label(part)} ({part.value or ''} {part.package or ''}) "
        f"→ {w:.1f}×{d:.1f}×{h:.1f} mm"
    )


def build_suggestion_plan(parts, organizers) -> str:
    """Pure, read-only suggestion of where unassigned parts could go.

    Returns a compact multi-line plan; never touches the database.
    """
    parts = sorted(
        list(parts),
        key=lambda p: ((p.value or "") or "", (p.internal_id or "") or ""),
    )
    organizers = sorted(
        list(organizers),
        key=lambda o: ((o.name or "") or "", str(getattr(o, "id", "") or "")),
    )

    used_ids = {id(o): set() for o in organizers}
    plan: list[tuple[Any, str, Any, tuple[float, float, float]]] = []
    need_new = []
    for part in parts:
        size = size_for_part(part)
        slot = None
        for o in organizers:
            comps = sorted(o.compartments, key=lambda c: (c.row, c.col))
            for c in comps:
                if c.part_id or c.id in used_ids[id(o)]:
                    continue
                if size[0] <= c.width and size[1] <= c.depth and size[2] <= c.height:
                    used_ids[id(o)].add(c.id)
                    slot = (o, _compartment_label(c), part, size)
                    break
            if slot:
                break
        if slot:
            plan.append(slot)
        else:
            need_new.append((part, size))

    groups: dict[str, list[tuple[Any, tuple[float, float, float]]]] = {}
    no_fit = []
    for part, size in need_new:
        preset = None
        for key in _PRESET_ORDER:
            inner_w, inner_d, inner_h = _organizer_preset_capacity(_ORGANIZER_PRESETS[key])
            if size[0] <= inner_w and size[1] <= inner_d and size[2] <= inner_h:
                preset = key
                break
        if preset:
            groups.setdefault(preset, []).append((part, size))
        else:
            no_fit.append((part, size))

    lines = [f"Organization plan ({len(parts)} unassigned parts, read-only):"]
    if plan:
        lines.append("\nExisting organizers:")
        for o in organizers:
            entries = [e for e in plan if e[0] is o]
            if not entries:
                continue
            lines.append(f"  {o.name}:")
            for _o, label, part, size in entries[:_MAX_PLAN_LINES]:
                lines.append(f"    - {label}: {_format_part(part, size)}")
            if len(entries) > _MAX_PLAN_LINES:
                lines.append(f"    … and {len(entries) - _MAX_PLAN_LINES} more")
    new_sections = [k for k in _PRESET_ORDER if groups.get(k)]
    if new_sections:
        lines.append("\nNew organizers to create:")
        for key in new_sections:
            entries = groups[key]
            preset = _ORGANIZER_PRESETS[key]
            specs = [
                CompartmentSpec(width=s[1][0], depth=s[1][1], height=s[1][2])
                for s in entries
            ]
            inner_w, inner_d, inner_h = _organizer_preset_capacity(preset)
            pack = pack_compartments(
                inner_w,
                inner_d,
                preset["divider_thickness"],
                specs,
                default_size=float(preset["default_size"]),
                default_height=inner_h,
            )
            lines.append(
                f"  new \"{preset['name']}\" (preset {key}): "
                f"{len(pack.cells)} of {len(entries)} parts fit"
            )
            for part, size in entries[:_MAX_PLAN_LINES]:
                lines.append(f"    - {_format_part(part, size)}")
            if len(entries) > _MAX_PLAN_LINES:
                lines.append(f"    … and {len(entries) - _MAX_PLAN_LINES} more")
    if no_fit:
        lines.append("\nStay unassigned (no organizer fits these):")
        for part, size in no_fit[:_MAX_PLAN_LINES]:
            lines.append(f"  - {_format_part(part, size)}")
        if len(no_fit) > _MAX_PLAN_LINES:
            lines.append(f"  … and {len(no_fit) - _MAX_PLAN_LINES} more")

    text = "\n".join(lines)
    if len(text) > 1200:
        text = text[:1200].rstrip() + "\n…"
    return text


def _tool_suggest_organization(db: Session, args: dict) -> str:
    parts = db.query(Part).filter(Part.storage_status == "unassigned").all()
    if not parts:
        return "All parts have assigned storage."
    organizers = (
        db.query(Organizer).order_by(Organizer.name.asc(), Organizer.id.asc()).all()
    )
    return build_suggestion_plan(parts, organizers)


TOOL_HANDLERS: dict[str, Any] = {
    "search_parts": _tool_search_parts,
    "get_part_details": _tool_get_part_details,
    "list_low_stock": _tool_list_low_stock,
    "list_unassigned": _tool_list_unassigned,
    "get_inventory": _tool_get_inventory,
    "list_locations": _tool_list_locations,
    "list_projects": _tool_list_projects,
    "get_project": _tool_get_project,
    "suggest_purchase": _tool_suggest_purchase,
    "count_inventory": _tool_count_inventory,
    "suggest_organization": _tool_suggest_organization,
}


# ── LLM client ────────────────────────────────────────────────────────────────

def _get_config() -> tuple[str, str, str]:
    settings = get_settings()
    base_url = settings.ai_resolved_url
    api_key = settings.ai_api_key or ""
    model = settings.ai_model or ""
    if not base_url or not model:
        raise ValueError("AI not configured — set AI_BASE_URL and AI_MODEL")
    return base_url, api_key, model


def provider_status() -> dict:
    """Return non-secret AI config state for the UI (never exposes the API key)."""
    settings = get_settings()
    base_url = settings.ai_resolved_url
    model = settings.ai_model or ""
    configured = bool(base_url and model)
    return {
        "configured": configured,
        "provider": base_url or None,
        "model": model or None,
    }


def _chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    stream: bool = False,
) -> dict:
    url = f"{base_url}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.3}
    if tools:
        body["tools"] = tools
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        detail = (e.response.text or "")[:300]
        raise AIError(
            f"AI provider returned HTTP {status}: {detail}", status=status
        ) from e
    except httpx.HTTPError as e:
        raise AIError(f"Could not reach AI provider: {e}") from e


def _chat_completion_stream(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
):
    url = f"{base_url}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "stream": True,
    }
    if tools:
        body["tools"] = tools
    try:
        client = httpx.Client(timeout=TIMEOUT)
        with client.stream("POST", url, json=body, headers=headers) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    yield json.loads(line[6:])
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        detail = (e.response.text or "")[:300]
        raise AIError(
            f"AI provider returned HTTP {status}: {detail}", status=status
        ) from e
    except httpx.HTTPError as e:
        raise AIError(f"Could not reach AI provider: {e}") from e


def _parse_tool_calls(choice: dict) -> list[dict]:
    msg = choice.get("message") or {}
    calls = msg.get("tool_calls") or []
    return [
        {
            "id": tc["id"],
            "name": tc["function"]["name"],
            "arguments": json.loads(tc["function"]["arguments"]),
        }
        for tc in calls
    ]


# ── Chat loop (multi-turn tool execution) ─────────────────────────────────────

def chat(db: Session, user_message: str, history: list[dict] | None = None) -> str:
    """Non-streaming chat: returns final text after any tool calls."""
    base_url, api_key, model = _get_config()
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    for _ in range(10):
        resp = _chat_completion(base_url, api_key, model, messages, tools=TOOLS)
        choice = resp.get("choices", [{}])[0]
        calls = _parse_tool_calls(choice)
        if not calls:
            return choice.get("message", {}).get("content") or ""
        tool_msg = choice.get("message", {})
        messages.append(tool_msg)
        for tc in calls:
            handler = TOOL_HANDLERS.get(tc["name"])
            if handler:
                result = handler(db, tc["arguments"])
            else:
                result = f"Unknown tool: {tc['name']}"
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    return "I took too many steps trying to answer that. Please try a simpler question."


def _stream_round(base_url, api_key, model, messages, tools, db):
    """Emit text deltas and tool-call events; return (content, calls, tool_results).

    Does NOT mutate *messages* — the caller is responsible for appending
    the assistant message and tool results in the correct order.
    """
    content_parts: list[str] = []
    tool_calls: dict[int, dict] = {}
    for chunk in _chat_completion_stream(base_url, api_key, model, messages, tools=tools):
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        if delta.get("content"):
            content_parts.append(delta["content"])
            yield json.dumps({"type": "text", "content": delta["content"]}) + "\n"
        for tc in delta.get("tool_calls") or []:
            idx = tc.get("index", 0)
            if idx not in tool_calls:
                tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
            if tc.get("id"):
                tool_calls[idx]["id"] = tc["id"]
            if tc.get("function", {}).get("name"):
                tool_calls[idx]["name"] = tc["function"]["name"]
            if tc.get("function", {}).get("arguments"):
                tool_calls[idx]["arguments"] += tc["function"]["arguments"]
    content = "".join(content_parts)
    calls = [
        {"id": tc["id"], "name": tc["name"], "arguments": json.loads(tc["arguments"] or "{}")}
        for tc in tool_calls.values()
    ]
    tool_results: list[dict] = []
    for tc in calls:
        yield json.dumps({"type": "tool_call", "name": tc["name"]}) + "\n"
        handler = TOOL_HANDLERS.get(tc["name"])
        result = handler(db, tc["arguments"]) if handler else f"Unknown tool: {tc['name']}"
        tool_results.append({"tool_call_id": tc["id"], "content": result})
        yield json.dumps({"type": "tool_result", "name": tc["name"], "content": result}) + "\n"
    return content, calls, tool_results


def _run_and_yield(gen):
    """Yield a generator's events, then return its (content, calls) return value."""
    try:
        while True:
            yield next(gen)
    except StopIteration as e:
        return e.value


def chat_stream(db: Session, user_message: str, history: list[dict] | None = None):
    """Streaming chat: yields JSON lines — text deltas and tool-call markers."""
    base_url, api_key, model = _get_config()
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    for _ in range(10):
        runner = _run_and_yield(
            _stream_round(base_url, api_key, model, messages, TOOLS, db)
        )
        try:
            while True:
                yield next(runner)
        except StopIteration as e:
            content, calls, tool_results = e.value
        if not calls:
            break
        messages.append({
            "role": "assistant",
            "content": content or None,
            "tool_calls": [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}}
                for tc in calls
            ],
        })
        for tr in tool_results:
            messages.append({"role": "tool", **tr})
    yield json.dumps({"type": "done"}) + "\n"
