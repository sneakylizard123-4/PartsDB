import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, Loading, Modal, errorMessage, useToast } from "../components/ui";
import type { SupplierCandidate } from "../types";

const SOURCES = [
  { value: "lcsc", label: "LCSC" },
  { value: "digikey", label: "DigiKey" },
];

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
