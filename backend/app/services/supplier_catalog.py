"""Modular supplier catalog integration (LCSC, DigiKey).

Each catalog implements a small interface with ``lookup`` (exact part number)
and ``search`` (keyword). All network errors and missing configuration are
surfaced as :class:`SupplierUnavailableError` so callers can fail gracefully —
the inventory system must keep working when external catalogs are down.
"""
from __future__ import annotations

import hashlib
import random
import string
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings

TIMEOUT = httpx.Timeout(20.0)
USER_AGENT = "PartsDB/0.1 (self-hosted electronics inventory)"

CATEGORY_KEYWORDS = [
    ("resistor", "Resistor"),
    ("capacitor", "Capacitor"),
    ("inductor", "Inductor"),
    ("diode", "Diode"),
    ("transistor", "Transistor"),
    ("led", "LED"),
    ("connector", "Connector"),
    ("switch", "Switch"),
    ("relay", "Relay"),
    ("fuse", "Fuse"),
    ("crystal", "Crystal"),
    ("oscillator", "Crystal"),
    ("battery", "Battery"),
    ("sensor", "Sensor"),
    ("module", "Module"),
    ("optoelectronic", "Optoelectronic"),
    ("display", "Display"),
    ("mounting", "Hardware"),
    ("screw", "Hardware"),
]

VALUE_SPECS = [
    "resistance",
    "capacitance",
    "inductance",
    "voltage - rated",
    "voltage rating",
    "rated voltage",
    "current rating",
    "rated current",
    "frequency",
    "supply voltage",
]


class SupplierUnavailableError(RuntimeError):
    """Raised when a supplier catalog cannot be reached or is not configured."""


def infer_category(*texts: str | None) -> str | None:
    joined = " ".join(t or "" for t in texts).lower()
    for keyword, label in CATEGORY_KEYWORDS:
        if keyword in joined:
            return label
    return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


@dataclass
class SupplierCandidate:
    source: str
    part_number: str
    mpn: str | None = None
    manufacturer: str | None = None
    description: str | None = None
    value: str | None = None
    package: str | None = None
    category: str | None = None
    datasheet_url: str | None = None
    price: float | None = None
    currency: str | None = None
    stock: int | None = None
    url: str | None = None
    specs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "part_number": self.part_number,
            "mpn": self.mpn,
            "manufacturer": self.manufacturer,
            "description": self.description,
            "value": self.value,
            "package": self.package,
            "category": self.category,
            "datasheet_url": self.datasheet_url,
            "price": self.price,
            "currency": self.currency,
            "stock": self.stock,
            "url": self.url,
            "specs": self.specs,
        }


def _specs_from_attrs(attrs: Any) -> dict[str, Any]:
    """Normalize LCSC ``productAttribute`` / DigiKey ``productDetails`` lists."""
    out: dict[str, Any] = {}
    if not isinstance(attrs, list):
        return out
    for item in attrs:
        if not isinstance(item, dict):
            continue
        label = item.get("attributeNameEn") or item.get("attributeName") or item.get(
            "label"
        ) or item.get("parameter")
        value = item.get("attributeValueEn") or item.get("attributeValue") or item.get(
            "value"
        )
        if label and value is not None:
            out[str(label).strip()] = value
    return out


def _value_from_specs(specs: dict[str, Any]) -> str | None:
    for label, value in specs.items():
        if any(key in label.lower() for key in VALUE_SPECS):
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip()):
                return str(value)
    return None


class BaseCatalog:
    source = ""

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT}

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers=self._headers()) as client:
                response = client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise SupplierUnavailableError(f"{self.source} network error: {exc}") from exc
        if response.status_code != 200:
            raise SupplierUnavailableError(
                f"{self.source} returned HTTP {response.status_code}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise SupplierUnavailableError(f"{self.source} returned invalid JSON") from exc


class LCSCCatalog(BaseCatalog):
    source = "lcsc"
    PUBLIC_BASE = "https://wmsc.lcsc.com/wmsc"
    AGENT_BASE = "https://ips.lcsc.com/rest/wmsc2agent"

    def __init__(self, settings) -> None:
        self.api_key = (settings.lcsc_api_key or "").strip()

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Referer": "https://www.lcsc.com/",
        }

    def _product_url(self, code: str) -> str:
        return f"https://www.lcsc.com/product-detail/{code}.html"

    def _price_info(self, raw: Any) -> tuple[float | None, str | None]:
        """Accept LCSC priceList (list) or price (dict) shapes."""
        currency = None
        prices: list[float] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    price = _to_float(
                        item.get("vipPrice") or item.get("price") or item.get("ladderPrice")
                    )
                    if price is not None:
                        prices.append(price)
                    if item.get("currency"):
                        currency = item.get("currency")
        elif isinstance(raw, dict):
            if raw.get("currency"):
                currency = raw.get("currency")
            for val in raw.values():
                if isinstance(val, (int, float)):
                    prices.append(float(val))
                elif isinstance(val, str):
                    p = _to_float(val)
                    if p is not None:
                        prices.append(p)
        prices = [p for p in prices if p > 0]
        return (min(prices) if prices else None, currency or "USD")

    def _candidate(self, raw: dict[str, Any]) -> SupplierCandidate:
        specs = _specs_from_attrs(
            raw.get("productAttribute")
            or raw.get("product_attribute")
            or raw.get("productDetails")
        )
        if not specs and isinstance(raw.get("specifications"), dict):
            specs = {k: str(v) for k, v in raw["specifications"].items()}

        code = raw.get("productCode") or raw.get("product_code") or raw.get("lcsc_part_number")
        price, currency = self._price_info(raw.get("priceList") or raw.get("price"))

        description = (
            raw.get("productIntroEn")
            or raw.get("product_intro_en")
            or raw.get("productDescriptionEn")
            or raw.get("productDescription")
            or raw.get("description")
        )
        package = (
            raw.get("encapStandard")
            or raw.get("package")
            or raw.get("packageEn")
            or raw.get("packageStandard")
        )
        category_hint = raw.get("catalogName") or raw.get("productGroupEn") or raw.get("category")
        category = (
            infer_category(category_hint, description, str(specs))
            if isinstance(category_hint, str)
            else infer_category(description, str(specs))
        )

        return SupplierCandidate(
            source=self.source,
            part_number=str(code),
            mpn=raw.get("productModel") or raw.get("mpn") or raw.get("product_model"),
            manufacturer=(
                raw.get("brandNameEn") or raw.get("brandName") or raw.get("manufacturer")
            ),
            description=description,
            value=raw.get("value") or _value_from_specs(specs),
            package=package,
            category=category,
            datasheet_url=raw.get("datasheetUrl") or raw.get("datasheet_url"),
            price=price,
            currency=currency,
            stock=_to_int(
                raw.get("supplyQty") or raw.get("stock") or raw.get("stock_number")
            ),
            url=raw.get("productUrl") or (self._product_url(str(code)) if code else None),
            specs=specs,
        )

    def _agent_signature(self, nonce: str, timestamp: str) -> str:
        raw = f"{self.api_key}{nonce}{timestamp}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _agent_lookup(self, code: str) -> SupplierCandidate:
        nonce = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        timestamp = str(int(time.time() * 1000))
        params = {
            "key": self.api_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "signature": self._agent_signature(nonce, timestamp),
            "product_number": code,
            "currency": "USD",
        }
        try:
            with httpx.Client(timeout=TIMEOUT, headers=self._headers()) as client:
                response = client.get(f"{self.AGENT_BASE}/product/detail", params=params)
        except httpx.HTTPError as exc:
            raise SupplierUnavailableError(f"lcsc agent network error: {exc}") from exc
        if response.status_code != 200:
            raise SupplierUnavailableError(f"lcsc agent returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise SupplierUnavailableError("lcsc agent returned invalid JSON") from exc
        result = payload.get("result")
        if not isinstance(result, dict) or not result:
            raise SupplierUnavailableError(
                f"lcsc agent error: {payload.get('msg') or 'empty result'}"
            )
        return self._candidate(result)

    def lookup(self, part_number: str) -> SupplierCandidate:
        code = part_number.strip()
        if not code:
            raise SupplierUnavailableError("Empty LCSC part number")
        if self.api_key:
            try:
                return self._agent_lookup(code)
            except SupplierUnavailableError:
                pass  # fall back to the public endpoint
        payload = self._get_json(
            f"{self.PUBLIC_BASE}/product/detail",
            {"product_code": code, "currency": "USD"},
        )
        if payload.get("code") not in (200, 0, None):
            raise SupplierUnavailableError(
                f"lcsc: {payload.get('msg') or 'product not found'} ({code})"
            )
        result = payload.get("result")
        if not isinstance(result, dict) or not result:
            raise SupplierUnavailableError(f"lcsc: product not found ({code})")
        candidate = self._candidate(result)
        if not candidate.part_number or candidate.part_number == "None":
            candidate.part_number = code
        return candidate

    def search(self, query: str) -> list[SupplierCandidate]:
        keyword = query.strip()
        if not keyword:
            raise SupplierUnavailableError("Empty LCSC search query")
        payload = self._get_json(
            f"{self.PUBLIC_BASE}/search/global",
            {"keyword": keyword, "currPage": 1, "pageSize": 8},
        )
        if payload.get("code") not in (200, 0, None):
            raise SupplierUnavailableError(
                f"lcsc: {payload.get('msg') or 'search failed'}"
            )
        result = payload.get("result") or {}
        if not isinstance(result, dict):
            raise SupplierUnavailableError("lcsc: unexpected search response")

        products = []
        products += self._extract_products(result.get("productSearchResultVO"))
        products += self._extract_products(result.get("productList"))

        tip = None
        tip_vo = result.get("tipProductDetailUrlVO") or result.get("tipProductVO")
        if isinstance(tip_vo, dict):
            tip = tip_vo.get("productCode") or tip_vo.get("product_code")

        candidates = [self._candidate(p) for p in products if isinstance(p, dict)]
        candidates = [c for c in candidates if c.part_number and c.part_number != "None"]
        if not candidates and tip:
            candidates.append(self.lookup(tip))
        return candidates

    def _extract_products(self, container: Any) -> list[dict[str, Any]]:
        if isinstance(container, dict):
            for key in ("productList", "products", "list", "items"):
                if isinstance(container.get(key), list):
                    return [p for p in container[key] if isinstance(p, dict)]
        if isinstance(container, list):
            return [p for p in container if isinstance(p, dict)]
        return []


class DigiKeyCatalog(BaseCatalog):
    source = "digikey"
    BASE = "https://api.digikey.com"

    def __init__(self, settings) -> None:
        self.client_id = (settings.digikey_client_id or "").strip()
        self.client_secret = (settings.digikey_client_secret or "").strip()
        self.static_token = (settings.digikey_api_token or "").strip()

    def _configured(self) -> bool:
        return bool(self.client_id and (self.client_secret or self.static_token))

    def _token(self) -> str:
        if self.static_token:
            return self.static_token
        try:
            with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
                response = client.post(
                    f"{self.BASE}/v1/oauth2/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "client_credentials",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.HTTPError as exc:
            raise SupplierUnavailableError(f"digikey OAuth network error: {exc}") from exc
        if response.status_code != 200:
            raise SupplierUnavailableError(
                f"digikey OAuth failed (HTTP {response.status_code}) — check client ID/secret"
            )
        token = response.json().get("access_token")
        if not token:
            raise SupplierUnavailableError("digikey OAuth returned no access token")
        return token

    def _headers(self) -> dict[str, str]:
        if not self._configured():
            raise SupplierUnavailableError(
                "DigiKey is not configured — set DIGIKEY_CLIENT_ID, "
                "DIGIKEY_CLIENT_SECRET (and optionally DIGIKEY_API_TOKEN)"
            )
        return {
            "User-Agent": USER_AGENT,
            "X-Digikey-Client-Id": self.client_id,
            "Authorization": f"Bearer {self._token()}",
            "X-DIGIKEY-LOCALE-SITE": "US",
            "X-DIGIKEY-LOCALE-LANGUAGE": "en",
            "X-DIGIKEY-LOCALE-CURRENCY": "USD",
            "X-DIGIKEY-LOCALE-SHIP-TO-COUNTRY": "US",
        }

    def _candidate(self, raw: dict[str, Any]) -> SupplierCandidate:
        specs = _specs_from_attrs(raw.get("productDetails"))
        if not specs and isinstance(raw.get("parameters"), list):
            specs = _specs_from_attrs(raw.get("parameters"))

        dk_number = (
            raw.get("digiKeyProductNumber")
            or raw.get("digikey_number")
            or raw.get("digiKeyPartNumber")
        )
        manufacturer = raw.get("manufacturer")
        if isinstance(manufacturer, dict):
            manufacturer = manufacturer.get("value") or manufacturer.get("name")
        mpn = (
            raw.get("manufacturerProductNumber")
            or raw.get("manufacturer_product_number")
            or raw.get("mpn")
        )

        price = None
        currency = "USD"
        pricing = raw.get("standardPricing") or raw.get("pricing")
        if isinstance(pricing, list) and pricing and isinstance(pricing[0], dict):
            first = min(
                pricing,
                key=lambda p: p.get("breakQuantity", 0) if isinstance(p, dict) else 0,
            )
            price = _to_float(
                first.get("unitPrice")
                or first.get("price")
                or (first.get("totalPrice") if first.get("breakQuantity") == 1 else None)
            )
            currency = raw.get("currency") or "USD"

        datasheet = None
        for key in ("primaryDatasheet", "datasheets", "datasheet"):
            value = raw.get(key)
            if isinstance(value, list) and value:
                first = value[0]
                datasheet = (
                    first.get("value") if isinstance(first, dict) else str(first)
                )
                break
            if isinstance(value, str):
                datasheet = value
                break

        category_hint = None
        taxonomy = raw.get("limitedTaxonomy") or raw.get("taxonomy")
        if isinstance(taxonomy, dict):
            cat = taxonomy.get("category")
            if isinstance(cat, dict):
                category_hint = cat.get("value")
            elif isinstance(cat, str):
                category_hint = cat
        category = infer_category(
            category_hint or raw.get("productType") or raw.get("category"),
            raw.get("productDescription"),
            str(specs),
        )

        package = None
        for label, value in specs.items():
            if any(key in label.lower() for key in ("package", "case", "encap")):
                if isinstance(value, str) and value.strip():
                    package = str(value)
                    break

        return SupplierCandidate(
            source=self.source,
            part_number=str(dk_number) if dk_number else "",
            mpn=mpn,
            manufacturer=manufacturer,
            description=raw.get("productDescription") or raw.get("description"),
            value=raw.get("value") or _value_from_specs(specs),
            package=raw.get("package") or package,
            category=category,
            datasheet_url=datasheet,
            price=price,
            currency=currency,
            stock=_to_int(raw.get("quantityAvailable") or raw.get("availability")),
            url=raw.get("productUrl"),
            specs=specs,
        )

    def _get_product(self, path: str) -> list[SupplierCandidate]:
        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers=self._headers()) as client:
                response = client.get(f"{self.BASE}{path}")
        except httpx.HTTPError as exc:
            raise SupplierUnavailableError(f"digikey network error: {exc}") from exc
        if response.status_code != 200:
            raise SupplierUnavailableError(
                f"digikey returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise SupplierUnavailableError("digikey returned invalid JSON") from exc
        if payload.get("ErrorResponseVersion"):
            raise SupplierUnavailableError(
                f"digikey error: {payload.get('ErrorMessage')}"
            )
        raw_products = payload.get("products")
        if isinstance(raw_products, list):
            return [
                self._candidate(p)
                for p in raw_products
                if isinstance(p, dict)
            ]
        return [self._candidate(payload)]

    def lookup(self, part_number: str) -> SupplierCandidate:
        pn = part_number.strip()
        if not pn:
            raise SupplierUnavailableError("Empty DigiKey part number")
        from urllib.parse import quote

        candidates = self._get_product(f"/products/v4/search/{quote(pn)}/productdetails")
        if not candidates:
            raise SupplierUnavailableError(f"digikey: product not found ({pn})")
        return candidates[0]

    def search(self, query: str) -> list[SupplierCandidate]:
        from urllib.parse import quote

        keyword = query.strip()
        if not keyword:
            raise SupplierUnavailableError("Empty DigiKey search query")
        candidates = self._get_product(
            f"/products/v4/search/keyword/{quote(keyword)}?limit=8&offset=0"
        )
        return candidates


def get_catalog(source: str) -> BaseCatalog:
    settings = get_settings()
    source = (source or "").strip().lower()
    if source == "lcsc":
        return LCSCCatalog(settings)
    if source == "digikey":
        return DigiKeyCatalog(settings)
    raise SupplierUnavailableError(f"Unknown supplier source: {source!r}")


def supplier_lookup(source: str, part_number: str) -> SupplierCandidate:
    return get_catalog(source).lookup(part_number)


def supplier_search(source: str, query: str) -> list[SupplierCandidate]:
    return get_catalog(source).search(query)
