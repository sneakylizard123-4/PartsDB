import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Badge, ErrorBox, Loading, Modal, errorMessage, useToast } from "../components/ui";
import type { SupplierCandidate, SupplierCompare, SupplierOffer } from "../types";

const SOURCES = [
  { value: "lcsc", label: "LCSC" },
  { value: "digikey", label: "DigiKey" },
];

function toCandidate(o: SupplierOffer): SupplierCandidate {
  return {
    source: o.source,
    part_number: o.part_number ?? o.part_label,
    mpn: o.mpn,
    manufacturer: o.manufacturer,
    description: o.description,
    value: o.value,
    package: o.package,
    category: null,
    msl: null,
    datasheet_url: null,
    price: o.price,
    currency: o.currency,
    stock: o.stock,
    url: o.url,
    specs: {},
  };
}

function ImportModal({
  candidate,
  onClose,
  onImported,
}: {
  candidate: SupplierCandidate;
  onClose: () => void;
  onImported: (partId: string) => void;
}) {
  const toast = useToast();
  const [locations, setLocations] = useState<{ id: string; name: string }[]>([]);
  const [ready, setReady] = useState(false);
  const [locationId, setLocationId] = useState("");
  const [qty, setQty] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .listLocations()
      .then((locs) => {
        setLocations(locs.map((l) => ({ id: l.id, name: l.full_path || l.name })));
        setReady(true);
      })
      .catch((err) => toast(errorMessage(err), "error"));
  }, []);

  const submit = async () => {
    const n = qty === "" ? undefined : Number(qty);
    if (qty !== "" && (!n || n <= 0)) {
      toast("Enter a positive quantity", "error");
      return;
    }
    setBusy(true);
    try {
      const part = await api.supplierImport({
        source: candidate.source,
        part_number: candidate.part_number,
        quantity: n,
        location_id: locationId || undefined,
      });
      toast("Part imported");
      onImported(part.id);
    } catch (err) {
      toast(errorMessage(err), "error");
      setBusy(false);
    }
  };

  return (
    <Modal title="Import part" onClose={onClose}>
      <div className="code-block mb">
        <strong>{candidate.mpn || candidate.part_number}</strong>
        {candidate.manufacturer && <div>{candidate.manufacturer}</div>}
        {candidate.value && <div>{candidate.value}</div>}
      </div>
      <div className="field">
        <label>Stock to location (optional)</label>
        <select value={locationId} onChange={(e) => setLocationId(e.target.value)} disabled={!ready}>
          <option value="">Don't add stock</option>
          {locations.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>Quantity</label>
        <input
          type="number"
          min={1}
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          placeholder="Leave empty to skip stock"
          disabled={!locationId}
        />
      </div>
      <div className="modal-actions">
        <button className="btn ghost" type="button" onClick={onClose}>
          Cancel
        </button>
        <button className="btn" onClick={submit} disabled={busy}>
          {busy ? "Importing…" : "Import"}
        </button>
      </div>
    </Modal>
  );
}

export default function SupplierImport() {
  const toast = useToast();
  const navigate = useNavigate();
  const [source, setSource] = useState("lcsc");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SupplierCandidate[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<SupplierCandidate | null>(null);

  const [compareQuery, setCompareQuery] = useState("");
  const [compare, setCompare] = useState<SupplierCompare | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState("");

  const search = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const q = query.trim();
    if (!q) {
      toast("Enter a search term or part number", "error");
      return;
    }
    setLoading(true);
    setError("");
    setResults(null);
    try {
      const found = await api.supplierLookup(source, q);
      setResults(found);
      if (found.length === 0) toast("No results found", "error");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const compareAll = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const q = compareQuery.trim();
    if (!q) {
      toast("Enter a search term or part number", "error");
      return;
    }
    setComparing(true);
    setCompareError("");
    setCompare(null);
    try {
      const res = await api.supplierCompare(q);
      setCompare(res);
      if (res.offers.length === 0) toast("No offers found", "error");
    } catch (err) {
      setCompareError(errorMessage(err));
    } finally {
      setComparing(false);
    }
  };

  const copyMpn = async (o: SupplierOffer) => {
    const text = o.mpn || o.part_number || o.part_label;
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied");
    } catch {
      toast("Could not copy", "error");
    }
  };

  const recommended = (o: SupplierOffer) =>
    compare?.recommendation &&
    compare.recommendation.source === o.source &&
    compare.recommendation.part_label === o.part_label;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Import from supplier</h1>
          <div className="sub">Search a supplier catalog and import parts into your library.</div>
        </div>
      </div>

      <div className="card mb" style={{ maxWidth: 760 }}>
        <form className="row" style={{ gap: 10 }} onSubmit={search}>
          <select value={source} onChange={(e) => setSource(e.target.value)} style={{ width: 130 }}>
            {SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <input
            style={{ flex: 1 }}
            placeholder="LCSC number (e.g. C25804 or 25804) or keyword…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </button>
        </form>
      </div>

      {error && <ErrorBox message={error} />}
      {loading && <Loading />}

      <div className="card mb" style={{ maxWidth: 760 }}>
        <h2>Compare suppliers</h2>
        <div className="muted small mb">
          Search LCSC and DigiKey side by side and get a recommendation based on price
          and stock.
        </div>
        <form className="row" style={{ gap: 10 }} onSubmit={compareAll}>
          <input
            style={{ flex: 1 }}
            placeholder="Part number or keyword…"
            value={compareQuery}
            onChange={(e) => setCompareQuery(e.target.value)}
          />
          <button className="btn" type="submit" disabled={comparing}>
            {comparing ? "Comparing…" : "Compare"}
          </button>
        </form>
      </div>

      {compareError && <ErrorBox message={compareError} />}
      {comparing && <Loading />}

      {!comparing && compare && (
        <div className="card mb">
          <div className="spread mb">
            <h2>Offers for “{compare.query}”</h2>
            <div className="muted small">{compare.offers.length} results</div>
          </div>
          {compare.warnings.length > 0 && (
            <div className="muted small mb">
              {compare.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}
          {compare.recommendation && (
            <div className="badge ok mb" style={{ display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
              <span className="dot" />
              <span>Recommended: {compare.recommendation.reason}</span>
            </div>
          )}
          <table className="table">
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Part</th>
                <th className="num">Price</th>
                <th className="num">Stock</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {compare.offers.map((o) => {
                const rec = recommended(o);
                return (
                  <tr
                    key={`${o.source}-${o.part_number}-${o.part_label}`}
                    className={rec ? "compare-recommended" : ""}
                  >
                    <td>
                      <strong>{o.supplier}</strong>
                      {rec && <div>
                        <Badge kind="ok">Recommended</Badge>
                      </div>}
                      <div className={`muted small ${o.in_stock ? "" : "err-text"}`}>
                        {o.in_stock ? `${o.stock} in stock` : "out of stock"}
                      </div>
                    </td>
                    <td>
                      <strong>{o.part_label}</strong>
                      {o.manufacturer && <div className="muted small">{o.manufacturer}</div>}
                      {o.value && <div className="mono small">{o.value}</div>}
                      {o.description && (
                        <div className="muted small">{o.description.slice(0, 80)}</div>
                      )}
                    </td>
                    <td className="num small">
                      {o.price !== null && o.price !== undefined
                        ? `${o.currency ?? ""} ${o.price}`
                        : "—"}
                    </td>
                    <td className="num small">{o.stock ?? "—"}</td>
                    <td className="small">
                      <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                        <button className="btn sm ghost" onClick={() => copyMpn(o)}>
                          copy MPN
                        </button>
                        {o.url && (
                          <a
                            className="btn sm ghost"
                            href={o.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            view
                          </a>
                        )}
                        <button className="btn sm" onClick={() => setSelected(toCandidate(o))}>
                          Import
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {compare.offers.length === 0 && (
                <tr>
                  <td colSpan={5} className="empty">
                    No offers found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {!loading && results && (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Part</th>
                <th>Package</th>
                <th>Category</th>
                <th className="num">Price</th>
                <th className="num">Stock</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {results.map((c) => {
                const specs = Object.entries(c.specs ?? {})
                  .slice(0, 3)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ");
                return (
                  <tr key={`${c.source}-${c.part_number}`}>
                    <td>
                      <strong>{c.mpn || c.part_number}</strong>
                      <div className="muted small">{c.manufacturer}</div>
                      {c.value && <div className="mono small">{c.value}</div>}
                      {specs && <div className="muted small">{specs}</div>}
                    </td>
                    <td className="mono small">
                      {c.package}
                      {c.msl && <div className="muted small">{c.msl}</div>}
                    </td>
                    <td className="small">{c.category}</td>
                    <td className="num small">
                      {c.price !== null && c.price !== undefined
                        ? `${c.currency ?? ""} ${c.price}`
                        : "—"}
                    </td>
                    <td className="num small">{c.stock ?? "—"}</td>
                    <td className="small">
                      <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                        {c.datasheet_url && (
                          <a
                            className="btn sm ghost"
                            href={c.datasheet_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            datasheet
                          </a>
                        )}
                        <button className="btn sm" onClick={() => setSelected(c)}>
                          Import
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <ImportModal
          candidate={selected}
          onClose={() => setSelected(null)}
          onImported={(partId) => navigate(`/parts/${partId}`)}
        />
      )}
    </div>
  );
}
