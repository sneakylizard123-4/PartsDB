import type {
  ApiKeyCreated,
  ApiKeyResponse,
  Attachment,
  BOM,
  BomItemMatch,
  CsvPreview,
  DashboardStats,
  InventoryItem,
  Location,
  LocationContents,
  LocationTreeNode,
  NormalizedBomItem,
  Organizer,
  OrganizerPreset,
  Page,
  Part,
  PartCreate,
  Project,
  ProjectRequirements,
  Reservation,
  SearchResult,
  ShoppingList,
  Supplier,
  SupplierCandidate,
  Transaction,
  UserResponse,
} from "./types";

const TOKEN_KEY = "partsdb_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  isBlob = false
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`/api${path}`, { ...options, headers });
  if (res.status === 401) {
    setToken(null);
    if (!path.startsWith("/auth/login")) window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }
  if (res.status === 204) return undefined as T;
  if (isBlob) return res as unknown as T;
  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail =
      (data as { detail?: string } | null)?.detail ??
      `Request failed (${res.status})`;
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data as T;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  // auth / account
  login: (username: string, password: string) =>
    request<TokenBody>("/auth/login", json("POST", { username, password })),
  me: () => request<UserResponse>("/auth/me"),
  listApiKeys: () => request<ApiKeyResponse[]>("/api-keys"),
  createApiKey: (name: string) =>
    request<ApiKeyCreated>("/api-keys", json("POST", { name })),
  revokeApiKey: (id: string) =>
    request<void>(`/api-keys/${id}`, json("DELETE")),

  // parts
  listParts: (params: Record<string, string | number | boolean> = {}) =>
    request<Page<Part>>(`/parts?${new URLSearchParams(Object.fromEntries(
      Object.entries(params).map(([k, v]) => [k, String(v)])
    ))}`),
  getPart: (id: string) => request<Part>(`/parts/${id}`),
  createPart: (body: PartCreate) => request<Part>("/parts", json("POST", body)),
  updatePart: (id: string, body: Partial<PartCreate>) =>
    request<Part>(`/parts/${id}`, json("PATCH", body)),
  deletePart: (id: string) => request<void>(`/parts/${id}`, json("DELETE")),
  addSupplierPart: (
    partId: string,
    body: { supplier_id: string; supplier_sku?: string; url?: string; price?: number; currency?: string; stock?: number }
  ) => request<unknown>(`/parts/${partId}/supplier-parts`, json("POST", body)),

  // inventory
  listInventory: (partId?: string, locationId?: string) => {
    const params = new URLSearchParams();
    if (partId) params.set("part_id", partId);
    if (locationId) params.set("location_id", locationId);
    return request<InventoryItem[]>(`/inventory?${params}`);
  },
  adjustInventory: (body: {
    part_id: string;
    location_id: string;
    quantity_change: number;
    reason?: string;
    notes?: string;
  }) => request<{ ok: boolean; transaction_id: string }>(
    "/inventory/adjust",
    json("POST", { reason: "adjustment", ...body })
  ),
  moveInventory: (body: {
    part_id: string;
    from_location_id: string;
    to_location_id: string;
    quantity: number;
    notes?: string;
  }) => request<{ ok: boolean; moved: number }>("/inventory/move", json("POST", body)),

  // transactions
  listTransactions: (params: Record<string, string | number> = {}) =>
    request<Page<Transaction>>(`/transactions?${new URLSearchParams(
      Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v)]))
    )}`),

  // locations
  listLocations: () => request<Location[]>("/locations"),
  getLocation: (id: string) => request<Location>(`/locations/${id}`),
  locationTree: () => request<LocationTreeNode[]>("/locations/tree"),
  locationContents: (id: string) =>
    request<LocationContents>(`/locations/${id}/contents`),
  createLocation: (body: { name: string; parent_id?: string | null; location_type?: string; notes?: string }) =>
    request<Location>("/locations", json("POST", body)),
  createDrawerGrid: (body: { name: string; parent_id?: string | null; rows: number; cols: number; notes?: string }) =>
    request<Location[]>("/locations/grid", json("POST", body)),
  deleteLocation: (id: string) => request<void>(`/locations/${id}`, json("DELETE")),

  // search
  search: (q: string) => request<SearchResult[]>(`/search?q=${encodeURIComponent(q)}`),

  // dashboard
  dashboard: () => request<DashboardStats>("/dashboard"),

  // projects
  listProjects: () => request<Project[]>("/projects"),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (body: { name: string; description?: string; build_qty?: number; status?: string }) =>
    request<Project>("/projects", json("POST", body)),
  updateProject: (id: string, body: Partial<{ name: string; description: string; build_qty: number; status: string }>) =>
    request<Project>(`/projects/${id}`, json("PATCH", body)),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, json("DELETE")),
  projectRequirements: (id: string) =>
    request<ProjectRequirements>(`/projects/${id}/requirements`),

  // boms
  listBoms: () => request<BOM[]>("/boms"),
  getBom: (id: string) => request<BOM>(`/boms/${id}`),
  createBom: (body: { project_id: string; name?: string; description?: string }) =>
    request<BOM>("/boms", json("POST", body)),
  deleteBom: (id: string) => request<void>(`/boms/${id}`, json("DELETE")),
  addBomItems: (bomId: string, items: NormalizedBomItem[]) =>
    request<BOM>(`/boms/${bomId}/items`, json("POST", items)),
  matchBom: (bomId: string) =>
    request<BomItemMatch[]>(`/boms/${bomId}/match`, json("POST")),
  matchBomItem: (bomId: string, itemId: string, body: { part_id: string; match_level: string; reason: string }) =>
    request<unknown>(`/boms/${bomId}/items/${itemId}/match`, json("POST", body)),
  previewCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<CsvPreview>("/boms/preview-csv", { method: "POST", body: form });
  },
  normalizeCsv: (rows: Record<string, string>[], mapping: Record<string, string>) =>
    request<NormalizedBomItem[]>("/boms/normalize", json("POST", { rows, mapping })),

  // reservations
  listReservations: (status = "active") =>
    request<Reservation[]>(`/reservations?status=${status}`),
  createReservation: (body: { project_id: string; part_id: string; quantity: number }) =>
    request<Reservation>("/reservations", json("POST", body)),
  fulfillReservation: (id: string) =>
    request<Reservation>(`/reservations/${id}/fulfill`, json("POST")),
  releaseReservation: (id: string) =>
    request<Reservation>(`/reservations/${id}/release`, json("POST")),

  // shopping lists
  listShoppingLists: () => request<ShoppingList[]>("/shopping-lists"),
  createShoppingList: (name = "Shopping List") =>
    request<ShoppingList>("/shopping-lists", json("POST", { name })),
  generateShoppingList: (projectId?: string) =>
    request<ShoppingList>(
      `/shopping-lists/generate${projectId ? `?project_id=${projectId}` : ""}`,
      json("POST")
    ),
  addShoppingItem: (listId: string, body: { part_id?: string; description?: string; quantity: number; notes?: string }) =>
    request<ShoppingList>(`/shopping-lists/${listId}/items`, json("POST", body)),
  removeShoppingItem: (listId: string, itemId: string) =>
    request<void>(`/shopping-lists/${listId}/items/${itemId}`, json("DELETE")),
  deleteShoppingList: (id: string) =>
    request<void>(`/shopping-lists/${id}`, json("DELETE")),

  // suppliers
  listSuppliers: () => request<Supplier[]>("/suppliers"),
  createSupplier: (body: { name: string; website?: string; notes?: string }) =>
    request<Supplier>("/suppliers", json("POST", body)),
  deleteSupplier: (id: string) => request<void>(`/suppliers/${id}`, json("DELETE")),
  supplierLookup: (source: string, q: string) =>
    request<SupplierCandidate[]>(
      `/suppliers/lookup?source=${encodeURIComponent(source)}&q=${encodeURIComponent(q)}`
    ),
  supplierImport: (body: {
    source: string;
    part_number: string;
    quantity?: number;
    location_id?: string;
  }) => request<Part>("/suppliers/import", json("POST", body)),

  // organizers
  organizerPresets: () => request<Record<string, OrganizerPreset>>("/organizers/presets"),
  listOrganizers: () => request<Organizer[]>("/organizers"),
  getOrganizer: (id: string) => request<Organizer>(`/organizers/${id}`),
  createOrganizer: (body: Record<string, unknown>) =>
    request<Organizer>("/organizers", json("POST", body)),
  assignOrganizer: (id: string, assignments: { compartment_id: string; part_id?: string; label?: string }[]) =>
    request<Organizer>(`/organizers/${id}/assign`, json("POST", assignments)),
  deleteOrganizer: (id: string) => request<void>(`/organizers/${id}`, json("DELETE")),

  // attachments
  listAttachments: (entityType?: string, entityId?: string) => {
    const params = new URLSearchParams();
    if (entityType) params.set("entity_type", entityType);
    if (entityId) params.set("entity_id", entityId);
    return request<Attachment[]>(`/attachments?${params}`);
  },
  uploadAttachment: (entityType: string, entityId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Attachment>(
      `/attachments?entity_type=${entityType}&entity_id=${entityId}`,
      { method: "POST", body: form }
    );
  },
  deleteAttachment: (id: string) => request<void>(`/attachments/${id}`, json("DELETE")),
  fetchDatasheet: (entityType: string, entityId: string, url: string) =>
    request<Attachment>(
      "/attachments/fetch",
      json("POST", { entity_type: entityType, entity_id: entityId, url })
    ),

  // backup
  createBackup: () => request<{ filename: string; created_at: string }>("/backup", json("POST")),
  listBackups: () => request<{ filename: string; created_at: string }[]>("/backup"),

  // ai
  aiChat: (message: string, history?: Array<{ role: string; content: string }>) =>
    request<{ response: string }>(
      "/ai/chat",
      json("POST", { message, history: history ?? [] }),
    ),
  aiStatus: () =>
    request<{ configured: boolean; provider: string | null; model: string | null }>(
      "/ai/status",
    ),
};

interface TokenBody {
  access_token: string;
  token_type: string;
  username: string;
}

export function downloadUrl(path: string): string {
  return `/api${path}`;
}

export async function aiChatStream(
  message: string,
  history: Array<{ role: string; content: string }> = [],
  onDelta: (text: string) => void,
  onToolCall?: (name: string) => void,
  onToolResult?: (name: string, content: string) => void,
  onDone?: () => void,
  onError?: (err: Error) => void,
) {
  const token = getToken();
  try {
    const resp = await fetch("/api/ai/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, history }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const reader = resp.body?.getReader();
    if (!reader) throw new Error("No response body");
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const evt = JSON.parse(line);
          if (evt.type === "text") onDelta(evt.content);
          else if (evt.type === "tool_call") onToolCall?.(evt.name);
          else if (evt.type === "tool_result") onToolResult?.(evt.name, evt.content);
          else if (evt.type === "done") onDone?.();
          else if (evt.type === "error") {
            onError?.(
              new Error(
                evt.message ||
                  "The AI provider could not complete the request. Check that it is configured and has credits.",
              ),
            );
            return;
          }
        } catch {
          // skip malformed lines
        }
      }
    }
    onDone?.();
  } catch (err) {
    onError?.(err instanceof Error ? err : new Error(String(err)));
  }
}
