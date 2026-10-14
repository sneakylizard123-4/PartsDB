export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---------- Auth / account ----------
export interface TokenResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string | null;
}

export interface ApiKeyResponse {
  id: string;
  name: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKeyResponse {
  key: string;
}

// ---------- Parts ----------
export interface Part {
  id: string;
  internal_id: string | null;
  manufacturer: string | null;
  mpn: string | null;
  lcsc_number: string | null;
  digikey_number: string | null;
  value: string | null;
  package: string | null;
  category: string | null;
  description: string | null;
  tolerance: string | null;
  voltage_rating: string | null;
  current_rating: string | null;
  msl: string | null;
  other_specs: Record<string, unknown>;
  datasheet_url: string | null;
  notes: string | null;
  min_qty: number | null;
  desired_qty: number | null;
  reorder_qty: number | null;
  storage_status: string;
  total_quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  low_stock: boolean;
  locations: {
    location_id: string;
    quantity: number;
    path: string;
  }[];
  supplier_parts: SupplierPart[];
  created_at: string;
  updated_at: string;
}

export interface SupplierPart {
  id: string;
  supplier_id: string;
  supplier_name: string | null;
  supplier_sku: string | null;
  url: string | null;
  price: number | null;
  currency: string | null;
  stock: number | null;
  price_breaks: Record<string, unknown>;
}

export interface PartCreate {
  internal_id?: string | null;
  manufacturer?: string | null;
  mpn?: string | null;
  lcsc_number?: string | null;
  digikey_number?: string | null;
  value?: string | null;
  package?: string | null;
  category?: string | null;
  description?: string | null;
  tolerance?: string | null;
  voltage_rating?: string | null;
  current_rating?: string | null;
  msl?: string | null;
  other_specs?: Record<string, unknown>;
  datasheet_url?: string | null;
  notes?: string | null;
  min_qty?: number | null;
  desired_qty?: number | null;
  reorder_qty?: number | null;
}

export interface PartFacets {
  categories: string[];
  packages: string[];
  manufacturers: string[];
  storage_statuses: string[];
}

// ---------- Locations ----------
export interface Location {
  id: string;
  name: string;
  parent_id: string | null;
  location_type: string | null;
  dimensions: Record<string, unknown>;
  notes: string | null;
  qr_code: string | null;
  full_path: string;
  children_count: number;
  created_at: string;
}

export interface LocationContents {
  location: Location;
  items: {
    id: string;
    part_id: string;
    quantity: number;
    internal_id: string | null;
    value: string | null;
    package: string | null;
    manufacturer: string | null;
    mpn: string | null;
  }[];
  children: Location[];
  compartments: {
    id: string;
    label: string | null;
    part_id: string | null;
    organizer_id: string;
  }[];
}

export interface LocationTreeNode {
  id: string;
  name: string;
  location_type: string | null;
  children: LocationTreeNode[];
}

// ---------- Inventory ----------
export interface InventoryItem {
  id: string;
  part_id: string;
  location_id: string;
  quantity: number;
  part_internal_id: string | null;
  part_value: string | null;
  part_package: string | null;
  part_manufacturer: string | null;
  part_mpn: string | null;
  location_path: string;
}

// ---------- Transactions ----------
export interface Transaction {
  id: string;
  part_id: string;
  location_id: string;
  quantity_change: number;
  reason: string | null;
  project_id: string | null;
  reservation_id: string | null;
  source: string | null;
  notes: string | null;
  timestamp: string;
  part_value: string | null;
  part_internal_id: string | null;
  location_path: string;
}

// ---------- AI ----------

export interface AiMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AiToolEvent {
  type: "tool_call" | "tool_result";
  name: string;
  content?: string;
}

// ---------- Suppliers ----------
export interface Supplier {
  id: string;
  name: string;
  website: string | null;
  notes: string | null;
  created_at: string;
}

// ---------- Projects ----------
export interface Project {
  id: string;
  name: string;
  description: string | null;
  build_qty: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectRequirement {
  part: {
    id: string;
    internal_id: string | null;
    value: string | null;
    package: string | null;
    mpn: string | null;
  } | null;
  required: number;
  available: number;
  reserved: number;
  missing: number;
  items: { id: string; designator: string; qty: number }[];
}

export interface ProjectRequirements {
  project: { id: string; name: string; build_qty: number };
  requirements: ProjectRequirement[];
}

// ---------- BOMs ----------
export interface BOMItem {
  id: string;
  designator: string;
  qty: number;
  value: string | null;
  footprint: string | null;
  mpn: string | null;
  manufacturer: string | null;
  description: string | null;
  matched_part_id: string | null;
  match_level: string | null;
  raw: Record<string, unknown>;
}

export interface BOMRevision {
  id: string;
  bom_id: string;
  version: number;
  comment: string | null;
  created_at: string;
}

export interface BOM {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  items: BOMItem[];
  revisions: BOMRevision[];
  created_at: string;
}

export interface BomItemMatch {
  bom_item_id: string;
  part_id: string;
  match_level: string;
  reason: string;
}

export interface CsvPreview {
  headers: string[];
  rows: Record<string, string>[];
  detected_mapping: Record<string, string>;
  total_rows: number;
}

export interface NormalizedBomItem {
  designator: string;
  qty: number;
  value: string | null;
  footprint: string | null;
  mpn: string | null;
  manufacturer: string | null;
  description: string | null;
}

export interface BomMatchCandidate {
  part_id: string;
  internal_id: string | null;
  value: string | null;
  package: string | null;
  manufacturer: string | null;
  mpn: string | null;
  match_level: string;
  reason: string;
  available_quantity: number | null;
}

export interface BomReviewItem {
  bom_id: string;
  bom_name: string;
  item_id: string;
  designator: string;
  qty: number;
  value: string | null;
  footprint: string | null;
  mpn: string | null;
  manufacturer: string | null;
  match_level: string | null;
  candidates: BomMatchCandidate[];
}

export interface BomReviewResponse {
  total: number;
  items: BomReviewItem[];
}

export interface BOMSnapshotItem {
  designator: string;
  qty: number;
  value: string | null;
  footprint: string | null;
  mpn: string | null;
  manufacturer: string | null;
}

export interface BomRevisionDiffItem {
  designator: string;
  status: "added" | "removed" | "changed" | "unchanged";
  from_item: BOMSnapshotItem | null;
  to_item: BOMSnapshotItem | null;
  qty_change: number;
  part: {
    id: string;
    internal_id: string | null;
    value: string | null;
    package: string | null;
    manufacturer: string | null;
    mpn: string | null;
  } | null;
  needed: number;
  available: number | null;
  shortfall: number;
}

export interface BomRevisionDiff {
  bom_id: string;
  bom_name: string;
  project_id: string;
  build_qty: number;
  from_revision: BOMRevision | null;
  to_revision: BOMRevision | null;
  items: BomRevisionDiffItem[];
  summary: {
    added: number;
    removed: number;
    changed: number;
    unchanged: number;
    total_shortfall: number;
  };
}

// ---------- Reservations ----------
export interface Reservation {
  id: string;
  project_id: string;
  part_id: string;
  quantity: number;
  status: string;
  project_name: string | null;
  part_value: string | null;
  part_internal_id: string | null;
  created_at: string;
}

// ---------- Shopping lists ----------
export interface ShoppingListSummary {
  available: number;
  reserved: number;
  missing: number;
  purchase: number;
}

export interface ShoppingListItem {
  id: string;
  part_id: string | null;
  description: string | null;
  quantity: number;
  status: string;
  source: string;
  notes: string | null;
  part_value: string | null;
  part_internal_id: string | null;
  available_quantity: number;
  reserved_quantity: number;
  missing_quantity: number;
  purchase_quantity: number;
}

export interface ShoppingList {
  id: string;
  name: string;
  status: string;
  created_at: string;
  items: ShoppingListItem[];
  summary: ShoppingListSummary;
}

// ---------- Organizers ----------
export interface Compartment {
  id: string;
  organizer_id: string;
  label: string | null;
  row: number;
  col: number;
  width: number;
  depth: number;
  height: number;
  part_id: string | null;
  location_id: string | null;
  part_value: string | null;
  location_path: string;
}

export interface Organizer {
  id: string;
  name: string;
  outer_width: number;
  outer_depth: number;
  outer_height: number;
  preset: string | null;
  wall_thickness: number;
  divider_thickness: number;
  clearance: number;
  config: Record<string, unknown>;
  storage_status: string;
  stl_path: string | null;
  compartments: Compartment[];
  created_at: string;
  note?: string | null;
}

export interface PartSize {
  part_id: string;
  width: number;
  depth: number;
  height: number;
  package: string | null;
  value: string | null;
}

export interface OrganizerPreset {
  name: string;
  outer_width: number;
  outer_depth: number;
  outer_height: number;
  default_size: number;
  wall_thickness: number;
  divider_thickness: number;
}

// ---------- Dashboard ----------
export interface MissingBomItem {
  item_id: string;
  bom_id: string;
  bom_name: string;
  project_id: string;
  project_name: string;
  designator: string;
  qty: number;
  needed: number;
  available: number;
  shortfall: number;
  value: string | null;
  footprint: string | null;
  mpn: string | null;
  manufacturer: string | null;
  matched_part_id: string | null;
}

export interface EmptyStorageLocation {
  id: string;
  name: string;
  full_path: string;
}

export interface DashboardStats {
  total_parts: number;
  low_stock_parts: number;
  missing_bom_components: number;
  missing_bom_items: MissingBomItem[];
  active_projects: number;
  shopping_requirements: number;
  recent_transactions: Transaction[];
  unassigned_parts: number;
  empty_storage: number;
  empty_storage_count: number;
  empty_storage_locations: EmptyStorageLocation[];
  recent_reservations: Reservation[];
  total_quantity: number;
}

// ---------- Search ----------
export interface SearchResult {
  id: string;
  type: "part" | "location" | "project" | "bom";
  title: string;
  subtitle: string | null;
  location_path: string | null;
}

export interface Attachment {
  id: string;
  entity_type: string;
  entity_id: string;
  filename: string;
  mime_type: string | null;
  size: number;
  kind: string;
  source_url: string | null;
  created_at: string;
}

// ---------- Supplier catalog ----------
export interface SupplierCandidate {
  source: string;
  part_number: string;
  mpn: string | null;
  manufacturer: string | null;
  description: string | null;
  value: string | null;
  package: string | null;
  category: string | null;
  msl: string | null;
  datasheet_url: string | null;
  price: number | null;
  currency: string | null;
  stock: number | null;
  url: string | null;
  specs: Record<string, string>;
}

export interface SupplierOffer {
  source: string;
  supplier: string;
  part_label: string;
  part_number: string | null;
  mpn: string | null;
  manufacturer: string | null;
  description: string | null;
  value: string | null;
  package: string | null;
  price: number | null;
  currency: string | null;
  stock: number | null;
  url: string | null;
  in_stock: boolean;
}

export interface SupplierRecommendation {
  source: string;
  part_label: string;
  reason: string;
}

export interface SupplierCompare {
  query: string;
  offers: SupplierOffer[];
  recommendation: SupplierRecommendation | null;
  warnings: string[];
}
