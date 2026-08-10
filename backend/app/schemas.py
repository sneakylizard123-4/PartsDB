from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


# ---------- Auth ----------


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(ORMModel):
    id: str
    name: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyResponse):
    key: str


class UserResponse(ORMModel):
    id: str
    username: str
    email: str | None


# ---------- Attachments ----------


class AttachmentFetchRequest(BaseModel):
    entity_type: str
    entity_id: str
    url: str


# ---------- Parts ----------


class PartCreate(BaseModel):
    internal_id: str | None = None
    manufacturer: str | None = None
    mpn: str | None = None
    lcsc_number: str | None = None
    digikey_number: str | None = None
    value: str | None = None
    package: str | None = None
    category: str | None = None
    description: str | None = None
    tolerance: str | None = None
    voltage_rating: str | None = None
    current_rating: str | None = None
    msl: str | None = None
    other_specs: dict[str, Any] = Field(default_factory=dict)
    datasheet_url: str | None = None
    notes: str | None = None
    min_qty: int | None = None
    desired_qty: int | None = None
    reorder_qty: int | None = None


class PartUpdate(BaseModel):
    internal_id: str | None = None
    manufacturer: str | None = None
    mpn: str | None = None
    lcsc_number: str | None = None
    digikey_number: str | None = None
    value: str | None = None
    package: str | None = None
    category: str | None = None
    description: str | None = None
    tolerance: str | None = None
    voltage_rating: str | None = None
    current_rating: str | None = None
    msl: str | None = None
    other_specs: dict[str, Any] | None = None
    datasheet_url: str | None = None
    notes: str | None = None
    min_qty: int | None = None
    desired_qty: int | None = None
    reorder_qty: int | None = None
    storage_status: str | None = None


class SupplierPartOut(ORMModel):
    id: str
    supplier_id: str
    supplier_name: str | None = None
    supplier_sku: str | None = None
    url: str | None = None
    price: float | None = None
    currency: str | None = None
    stock: int | None = None
    price_breaks: dict[str, Any] = Field(default_factory=dict)


class PartOut(ORMModel):
    id: str
    internal_id: str | None
    manufacturer: str | None
    mpn: str | None
    lcsc_number: str | None
    digikey_number: str | None
    value: str | None
    package: str | None
    category: str | None
    description: str | None
    tolerance: str | None
    voltage_rating: str | None
    current_rating: str | None
    msl: str | None
    other_specs: dict[str, Any] = Field(default_factory=dict)
    datasheet_url: str | None
    notes: str | None
    min_qty: int | None
    desired_qty: int | None
    reorder_qty: int | None
    storage_status: str
    total_quantity: int = 0
    reserved_quantity: int = 0
    available_quantity: int = 0
    low_stock: bool = False
    locations: list[dict[str, Any]] = Field(default_factory=list)
    supplier_parts: list[SupplierPartOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------- Locations ----------


class LocationCreate(BaseModel):
    name: str
    parent_id: str | None = None
    location_type: str = "compartment"
    dimensions: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    location_type: str | None = None
    dimensions: dict[str, Any] | None = None
    notes: str | None = None


class LocationOut(ORMModel):
    id: str
    name: str
    parent_id: str | None
    location_type: str | None
    dimensions: dict[str, Any] = Field(default_factory=dict)
    notes: str | None
    qr_code: str | None
    full_path: str = ""
    children_count: int = 0
    created_at: datetime


# ---------- Inventory ----------


class InventoryItemOut(ORMModel):
    id: str
    part_id: str
    location_id: str
    quantity: int
    part_internal_id: str | None = None
    part_value: str | None = None
    part_package: str | None = None
    part_manufacturer: str | None = None
    part_mpn: str | None = None
    location_path: str = ""


class InventoryAdjust(BaseModel):
    part_id: str
    location_id: str
    quantity_change: int
    reason: str = "adjustment"
    project_id: str | None = None
    notes: str | None = None
    source: str = "web"


class MoveInventory(BaseModel):
    part_id: str
    from_location_id: str
    to_location_id: str
    quantity: int = Field(gt=0)
    notes: str | None = None


# ---------- Transactions ----------


class TransactionOut(ORMModel):
    id: str
    part_id: str
    location_id: str
    quantity_change: int
    reason: str | None
    project_id: str | None
    reservation_id: str | None
    source: str | None
    notes: str | None
    timestamp: datetime
    part_value: str | None = None
    part_internal_id: str | None = None
    location_path: str = ""


# ---------- Suppliers ----------


class SupplierCreate(BaseModel):
    name: str
    website: str | None = None
    notes: str | None = None


class SupplierOut(ORMModel):
    id: str
    name: str
    website: str | None
    notes: str | None
    created_at: datetime


class SupplierCandidateOut(BaseModel):
    source: str
    part_number: str
    mpn: str | None = None
    manufacturer: str | None = None
    description: str | None = None
    value: str | None = None
    package: str | None = None
    category: str | None = None
    msl: str | None = None
    datasheet_url: str | None = None
    price: float | None = None
    currency: str | None = None
    stock: int | None = None
    url: str | None = None
    specs: dict[str, Any] = Field(default_factory=dict)


class SupplierImportRequest(BaseModel):
    source: str
    part_number: str
    quantity: int | None = Field(default=None, ge=0)
    location_id: str | None = None



class SupplierPartCreate(BaseModel):
    part_id: str
    supplier_sku: str | None = None
    url: str | None = None
    price: float | None = None
    currency: str = "USD"
    stock: int | None = None
    price_breaks: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    datasheet_url: str | None = None


# ---------- Projects ----------


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    build_qty: int = 1
    status: str = "active"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    build_qty: int | None = None
    status: str | None = None


class ProjectOut(ORMModel):
    id: str
    name: str
    description: str | None
    build_qty: int
    status: str
    created_at: datetime
    updated_at: datetime


# ---------- BOMs ----------


class BOMItemCreate(BaseModel):
    designator: str
    qty: int = 1
    value: str | None = None
    footprint: str | None = None
    mpn: str | None = None
    manufacturer: str | None = None
    description: str | None = None


class BOMCreate(BaseModel):
    project_id: str
    name: str = "BOM"
    description: str | None = None


class BOMItemOut(ORMModel):
    id: str
    designator: str
    qty: int
    value: str | None
    footprint: str | None
    mpn: str | None
    manufacturer: str | None
    description: str | None
    matched_part_id: str | None
    match_level: str | None
    raw: dict[str, Any] = Field(default_factory=dict)


class BOMOut(ORMModel):
    id: str
    project_id: str
    name: str
    description: str | None
    items: list[BOMItemOut] = Field(default_factory=list)
    revisions: list["BOMRevisionOut"] = Field(default_factory=list)
    created_at: datetime


class BOMRevisionOut(ORMModel):
    id: str
    bom_id: str
    version: int
    comment: str | None
    created_at: datetime


class BomItemMatch(BaseModel):
    bom_item_id: str
    part_id: str
    match_level: str
    reason: str


# ---------- Reservations ----------


class ReservationCreate(BaseModel):
    project_id: str
    part_id: str
    quantity: int = Field(gt=0)


class ReservationOut(ORMModel):
    id: str
    project_id: str
    part_id: str
    quantity: int
    status: str
    project_name: str | None = None
    part_value: str | None = None
    part_internal_id: str | None = None


# ---------- Shopping lists ----------


class ShoppingListCreate(BaseModel):
    name: str = "Shopping List"


class ShoppingListItemCreate(BaseModel):
    part_id: str | None = None
    description: str | None = None
    quantity: int = Field(gt=0)
    notes: str | None = None


class ShoppingListItemOut(ORMModel):
    id: str
    part_id: str | None
    description: str | None
    quantity: int
    status: str
    source: str
    notes: str | None
    part_value: str | None = None
    part_internal_id: str | None = None


class ShoppingListOut(ORMModel):
    id: str
    name: str
    status: str
    created_at: datetime
    items: list[ShoppingListItemOut] = Field(default_factory=list)


# ---------- Organizers ----------


class CompartmentRequirement(BaseModel):
    label: str
    part_id: str | None = None
    width: float | None = None
    depth: float | None = None
    height: float | None = None


class OrganizerGenerate(BaseModel):
    name: str = "Organizer"
    outer_width: float
    outer_depth: float
    outer_height: float
    preset: str | None = None
    wall_thickness: float = 1.2
    divider_thickness: float = 1.2
    clearance: float = 0.2
    compartments: list[CompartmentRequirement] = Field(default_factory=list)


class CompartmentOut(ORMModel):
    id: str
    organizer_id: str
    label: str | None
    row: int
    col: int
    width: float
    depth: float
    height: float
    part_id: str | None
    location_id: str | None
    part_value: str | None = None
    location_path: str = ""


class OrganizerOut(ORMModel):
    id: str
    name: str
    outer_width: float
    outer_depth: float
    outer_height: float
    preset: str | None
    wall_thickness: float
    divider_thickness: float
    clearance: float
    config: dict[str, Any] = Field(default_factory=dict)
    storage_status: str
    stl_path: str | None
    compartments: list[CompartmentOut] = Field(default_factory=list)
    created_at: datetime


# ---------- Dashboard ----------


class DashboardStats(BaseModel):
    total_parts: int
    low_stock_parts: int
    missing_bom_components: int
    active_projects: int
    shopping_requirements: int
    recent_transactions: list[TransactionOut]
    unassigned_parts: int
    empty_storage: int
    recent_reservations: list[ReservationOut]
    total_quantity: int


# ---------- Search ----------


class SearchResult(BaseModel):
    id: str
    type: str  # part | location | project | bom
    title: str
    subtitle: str | None = None
    location_path: str | None = None


# ---------- Backup ----------


class BackupOut(BaseModel):
    filename: str
    created_at: datetime


BOMOut.model_rebuild()
