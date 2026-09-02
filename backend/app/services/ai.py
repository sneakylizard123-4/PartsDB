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
from app.models.part import Part
from app.models.project import Project
from app.models.reservation import Reservation
from app.services.bom_matching import match_bom_item
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
