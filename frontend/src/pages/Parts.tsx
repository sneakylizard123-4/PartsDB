import { useMemo, useState } from "react";
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
import type { PartCreate } from "../types";

export default function Parts() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const toast = useToast();
  const navigate = useNavigate();

  const params = useMemo(() => {
    const p: Record<string, string | number | boolean> = { limit: 100 };
    if (q) p["q"] = q;
    if (category) p["category"] = category;
    if (lowOnly) p["low_stock_only"] = true;
    return p;
  }, [q, category, lowOnly]);

  const { data, loading, error, reload } = useAsync(
    () => api.listParts(params),
    [params]
  );

  const loadCategories = () =>
    api.listParts({ limit: 200 }).then((d) => {
      const cats = new Set(d.items.map((p) => p.category).filter(Boolean) as string[]);
      setCategories([...cats].sort());
    });

  useMemo(() => {
    void loadCategories();
  }, []);

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
            placeholder="Filter parts…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <label className="row" style={{ cursor: "pointer" }}>
          <input type="checkbox" checked={lowOnly} onChange={(e) => setLowOnly(e.target.checked)} />
          Low stock only
        </label>
      </div>

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
