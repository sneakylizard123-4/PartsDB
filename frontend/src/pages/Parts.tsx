import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import {
  ErrorBox,
  Loading,
  Modal,
  Quantity,
  errorMessage,
  stockBadge,
  useAsync,
  useToast,
} from "../components/ui";
import PartForm from "../components/PartForm";
import type { Location, PartCreate, PartFacets } from "../types";

const STOCK_STATUSES = [
  { value: "", label: "Any stock" },
  { value: "in_stock", label: "In stock" },
  { value: "low", label: "Low stock" },
  { value: "out", label: "Out of stock" },
  { value: "reserved", label: "Fully reserved" },
];

const SORTS = [
  { value: "created_desc", label: "Newest first" },
  { value: "internal_id", label: "Internal ID" },
  { value: "value", label: "Value" },
  { value: "manufacturer", label: "Manufacturer" },
];

export default function Parts() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [packageName, setPackageName] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [locationId, setLocationId] = useState("");
  const [storageStatus, setStorageStatus] = useState("");
  const [stockStatus, setStockStatus] = useState("");
  const [minQty, setMinQty] = useState("");
  const [maxQty, setMaxQty] = useState("");
  const [minVoltage, setMinVoltage] = useState("");
  const [maxVoltage, setMaxVoltage] = useState("");
  const [sortBy, setSortBy] = useState("created_desc");
  const [showFilters, setShowFilters] = useState(false);
  const [facets, setFacets] = useState<PartFacets | null>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();

  const params = useMemo(() => {
    const p: Record<string, string | number | boolean> = { limit: 100, sort_by: sortBy };
    if (q) p["q"] = q;
    if (category) p["category"] = category;
    if (packageName) p["package"] = packageName;
    if (manufacturer) p["manufacturer"] = manufacturer;
    if (locationId) p["location_id"] = locationId;
    if (storageStatus) p["storage_status"] = storageStatus;
    if (stockStatus) p["stock_status"] = stockStatus;
    if (minQty) p["min_qty"] = minQty;
    if (maxQty) p["max_qty"] = maxQty;
    if (minVoltage) p["min_voltage"] = minVoltage;
    if (maxVoltage) p["max_voltage"] = maxVoltage;
    return p;
  }, [
    q,
    category,
    packageName,
    manufacturer,
    locationId,
    storageStatus,
    stockStatus,
    minQty,
    maxQty,
    minVoltage,
    maxVoltage,
    sortBy,
  ]);

  const { data, loading, error, reload } = useAsync(
    () => api.listParts(params),
    [params]
  );

  useEffect(() => {
    api.partFacets().then(setFacets).catch(() => undefined);
    api.listLocations().then(setLocations).catch(() => undefined);
  }, []);

  const activeFilters = [
    category,
    packageName,
    manufacturer,
    locationId,
    storageStatus,
    stockStatus,
    minQty,
    maxQty,
    minVoltage,
    maxVoltage,
  ].filter(Boolean).length;

  const clearFilters = () => {
    setCategory("");
    setPackageName("");
    setManufacturer("");
    setLocationId("");
    setStorageStatus("");
    setStockStatus("");
    setMinQty("");
    setMaxQty("");
    setMinVoltage("");
    setMaxVoltage("");
  };

  const create = async (body: PartCreate) => {
    try {
      const part = await api.createPart(body);
      toast("Part created");
      setShowCreate(false);
      navigate(`/parts/${part.id}`);
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const shown = data?.items ?? [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Parts</h1>
          <div className="sub">{data ? `${data.total} parts` : ""}</div>
        </div>
        <div className="actions">
          <button className="btn" onClick={() => setShowCreate(true)}>
            + Add Part
          </button>
        </div>
      </div>

      <div className="row mb">
        <div className="search-wrap">
          <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            placeholder="Search value, MPN, LCSC, description…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <button
          className="btn ghost"
          onClick={() => setShowFilters((v) => !v)}
        >
          Filters{activeFilters ? ` (${activeFilters})` : ""}
        </button>
      </div>

      {showFilters && (
        <div className="card mb">
          <div className="spread mb">
            <h2>Filters</h2>
            <button
              className="btn ghost sm"
              onClick={clearFilters}
              disabled={!activeFilters}
            >
              Clear
            </button>
          </div>
          <div className="form-row">
            <div className="field">
              <label>Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">All categories</option>
                {(facets?.categories ?? []).map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Package</label>
              <select value={packageName} onChange={(e) => setPackageName(e.target.value)}>
                <option value="">All packages</option>
                {(facets?.packages ?? []).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Manufacturer</label>
              <select value={manufacturer} onChange={(e) => setManufacturer(e.target.value)}>
                <option value="">All manufacturers</option>
                {(facets?.manufacturers ?? []).map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Location</label>
              <select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
                <option value="">Any location</option>
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.full_path}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Stock status</label>
              <select value={stockStatus} onChange={(e) => setStockStatus(e.target.value)}>
                {STOCK_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Storage status</label>
              <select value={storageStatus} onChange={(e) => setStorageStatus(e.target.value)}>
                <option value="">Any</option>
                {(facets?.storage_statuses ?? []).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Quantity at least</label>
              <input
                type="number"
                min={0}
                value={minQty}
                onChange={(e) => setMinQty(e.target.value)}
                placeholder="0"
              />
            </div>
            <div className="field">
              <label>Quantity at most</label>
              <input
                type="number"
                min={0}
                value={maxQty}
                onChange={(e) => setMaxQty(e.target.value)}
                placeholder="∞"
              />
            </div>
            <div className="field">
              <label>Min voltage</label>
              <input
                value={minVoltage}
                onChange={(e) => setMinVoltage(e.target.value)}
                placeholder="e.g. 16"
              />
            </div>
            <div className="field">
              <label>Max voltage</label>
              <input
                value={maxVoltage}
                onChange={(e) => setMaxVoltage(e.target.value)}
                placeholder="e.g. 50"
              />
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Internal ID</th>
                <th>Value</th>
                <th>Package</th>
                <th>MPN</th>
                <th>Status</th>
                <th className="num">Total</th>
                <th className="num">Reserved</th>
                <th className="num">Available</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link className="link mono" to={`/parts/${p.id}`}>
                      {p.internal_id || "—"}
                    </Link>
                  </td>
                  <td>{p.value || <span className="muted">—</span>}</td>
                  <td className="mono">{p.package || "—"}</td>
                  <td className="mono muted">{p.mpn || "—"}</td>
                  <td>{stockBadge(p)}</td>
                  <td className="num">
                    <Quantity value={p.total_quantity} />
                  </td>
                  <td className="num muted">{p.reserved_quantity}</td>
                  <td className="num">{p.available_quantity}</td>
                </tr>
              ))}
              {shown.length === 0 && (
                <tr>
                  <td colSpan={8} className="empty">
                    No parts found. Add your first part.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <Modal title="Add part" onClose={() => setShowCreate(false)} wide>
          <PartForm onSubmit={create} />
        </Modal>
      )}
    </div>
  );
}
