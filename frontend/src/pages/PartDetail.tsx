import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import {
  Badge,
  ErrorBox,
  Loading,
  Modal,
  Quantity,
  errorMessage,
  formatDate,
  stockBadge,
  storageStatusBadge,
  useAsync,
  useToast,
} from "../components/ui";
import PartForm from "../components/PartForm";
import type { Part, PartCreate, Reservation } from "../types";

type TxnType = "add" | "remove" | "move";

function AdjustModal({
  part,
  onClose,
}: {
  part: Part;
  onClose: () => void;
}) {
  const [type, setType] = useState<TxnType>("add");
  const [locationId, setLocationId] = useState(part.locations[0]?.location_id ?? "");
  const [toLocationId, setToLocationId] = useState("");
  const [qty, setQty] = useState("");
  const [reason, setReason] = useState("restock");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const [locations, setLocations] = useState<{ id: string; name: string }[]>([]);
  const [ready, setReady] = useState(false);

  useAsync(async () => {
    const locs = await api.listLocations();
    const mapped = locs.map((l) => ({ id: l.id, name: l.full_path || l.name }));
    setLocations(mapped);
    setLocationId((cur) => cur || mapped[0]?.id || "");
    setReady(true);
    return null;
  }, []);

  const submit = async () => {
    const n = Number(qty);
    if (!n || n <= 0) {
      toast("Enter a quantity", "error");
      return;
    }
    setBusy(true);
    try {
      if (type === "move") {
        await api.moveInventory({
          part_id: part.id,
          from_location_id: locationId,
          to_location_id: toLocationId,
          quantity: n,
        });
        toast("Moved stock");
      } else {
        await api.adjustInventory({
          part_id: part.id,
          location_id: locationId,
          quantity_change: type === "add" ? n : -n,
          reason,
        });
        toast(type === "add" ? "Stock added" : "Stock removed");
      }
      onClose();
      window.location.reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Adjust inventory" onClose={onClose}>
      <div className="form-row mb">
        {(["add", "remove", "move"] as TxnType[]).map((t) => (
          <button
            key={t}
            className={`btn ${type === t ? "" : "ghost"}`}
            onClick={() => setType(t)}
          >
            {t === "add" ? "+ Add" : t === "remove" ? "− Remove" : "↔ Move"}
          </button>
        ))}
      </div>
      <div className="field">
        <label>{type === "move" ? "From location" : "Location"}</label>
        <select value={locationId} onChange={(e) => setLocationId(e.target.value)} disabled={!ready}>
          {!locationId && <option value="">Select location…</option>}
          {locations.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>
      {type === "move" && (
        <div className="field">
          <label>To location</label>
          <select value={toLocationId} onChange={(e) => setToLocationId(e.target.value)} disabled={!ready}>
            <option value="">Select destination…</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="form-row">
        <div className="field">
          <label>Quantity</label>
          <input type="number" value={qty} onChange={(e) => setQty(e.target.value)} autoFocus />
        </div>
        <div className="field">
          <label>Reason</label>
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="restock, usage…" />
        </div>
      </div>
      <div className="modal-actions">
        <button className="btn ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn" onClick={submit} disabled={busy || !locationId || (type === "move" && !toLocationId)}>
          {busy ? "Saving…" : "Confirm"}
        </button>
      </div>
    </Modal>
  );
}

export default function PartDetail() {
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const navigate = useNavigate();
  const [showAdjust, setShowAdjust] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showSupplier, setShowSupplier] = useState(false);
  const [showReserve, setShowReserve] = useState(false);
  const [showUrlFetch, setShowUrlFetch] = useState(false);
  const [urlInput, setUrlInput] = useState("");

  const { data: part, loading, error, reload } = useAsync(
    () => api.getPart(id!),
    [id]
  );

  const { data: txns } = useAsync(() => api.listTransactions({ part_id: id!, limit: 25 }), [id]);
  const { data: reservations } = useAsync(() => api.listReservations("active"), [id]);
  const { data: attachments, reload: reloadAtts } = useAsync(
    () => api.listAttachments("part", id!),
    [id]
  );
  const { data: projects } = useAsync(() => api.listProjects(), []);
  const { data: suppliers } = useAsync(() => api.listSuppliers(), []);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!part) return null;

  const partReservations = (reservations ?? []).filter((r) => r.part_id === part.id);
  const partTxns = txns?.items ?? [];

  const update = async (body: PartCreate) => {
    try {
      await api.updatePart(part.id, body);
      toast("Part updated");
      setShowEdit(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const remove = async () => {
    if (!confirm(`Delete part ${part.internal_id || part.value || ""}? This cannot be undone.`))
      return;
    try {
      await api.deletePart(part.id);
      toast("Part deleted");
      navigate("/parts");
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const addSupplierPart = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await api.addSupplierPart(part.id, {
        supplier_id: String(fd.get("supplier_id")),
        supplier_sku: String(fd.get("supplier_sku") || "") || undefined,
        url: String(fd.get("url") || "") || undefined,
        price: fd.get("price") ? Number(fd.get("price")) : undefined,
        stock: fd.get("stock") ? Number(fd.get("stock")) : undefined,
      });
      toast("Supplier part added");
      setShowSupplier(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const reserve = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await api.createReservation({
        project_id: String(fd.get("project_id")),
        part_id: part.id,
        quantity: Number(fd.get("quantity")),
      });
      toast("Reserved");
      setShowReserve(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await api.uploadAttachment("part", part.id, file);
      toast("Attachment uploaded");
      reloadAtts();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const downloadDatasheet = async (url?: string) => {
    const target = url || part.datasheet_url;
    if (!target) {
      toast("No datasheet URL set", "error");
      return;
    }
    try {
      await api.fetchDatasheet("part", part.id, target);
      toast("Datasheet saved locally");
      reloadAtts();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const fetchFromUrl = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!urlInput.trim()) return;
    await downloadDatasheet(urlInput.trim());
    setUrlInput("");
    setShowUrlFetch(false);
  };

  const specRows: [string, string][] = [
    ["Manufacturer", part.manufacturer ?? ""],
    ["MPN", part.mpn ?? ""],
    ["LCSC", part.lcsc_number ?? ""],
    ["DigiKey", part.digikey_number ?? ""],
    ["Tolerance", part.tolerance ?? ""],
    ["Voltage", part.voltage_rating ?? ""],
    ["Current", part.current_rating ?? ""],
    ["MSL", part.msl ?? ""],
    ["Category", part.category ?? ""],
    ["Min qty", part.min_qty?.toString() ?? ""],
    ["Desired qty", part.desired_qty?.toString() ?? ""],
    ["Reorder qty", part.reorder_qty?.toString() ?? ""],
    ["Datasheet", part.datasheet_url ?? ""],
  ].filter(([, v]) => v) as [string, string][];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="mono">{part.internal_id || "Part"}</h1>
          <div className="sub">
            {[part.value, part.package, part.description].filter(Boolean).join(" · ")}
          </div>
          <div className="row mt">
            {stockBadge(part)}
            {storageStatusBadge(part.storage_status)}
          </div>
        </div>
        <div className="actions">
          <button className="btn" onClick={() => setShowAdjust(true)}>
            + / − Stock
          </button>
          <button className="btn ghost" onClick={() => setShowReserve(true)}>
            Reserve
          </button>
          <button className="btn ghost" onClick={() => setShowEdit(true)}>
            Edit
          </button>
          <button className="btn danger" onClick={remove}>
            Delete
          </button>
        </div>
      </div>

      <div className="grid cols-3">
        <div className="card">
          <h2>Stock</h2>
          <div className="row" style={{ gap: 22 }}>
            <div>
              <div className="stat" style={{ boxShadow: "none", border: "none", padding: 0 }}>
                <div className="value">{part.total_quantity}</div>
                <div className="label">Total</div>
              </div>
            </div>
            <div>
              <div className="stat" style={{ boxShadow: "none", border: "none", padding: 0 }}>
                <div className="value warn">{part.reserved_quantity}</div>
                <div className="label">Reserved</div>
              </div>
            </div>
            <div>
              <div className="stat" style={{ boxShadow: "none", border: "none", padding: 0 }}>
                <div className="value ok">{part.available_quantity}</div>
                <div className="label">Available</div>
              </div>
            </div>
          </div>
          <div className="mt">
            {part.locations.length === 0 && <div className="muted small">No stock on hand.</div>}
            {part.locations.map((l) => (
              <div key={l.location_id} className="row mb" style={{ justifyContent: "space-between" }}>
                <Link className="link mono small" to={`/locations/${l.location_id}`}>
                  📍 {l.path}
                </Link>
                <strong className="num">
                  <Quantity value={l.quantity} />
                </strong>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Specifications</h2>
          {specRows.length === 0 && <div className="muted small">No specifications.</div>}
          {specRows.map(([k, v]) => (
            <div key={k} className="row mb" style={{ justifyContent: "space-between" }}>
              <span className="muted small">{k}</span>
              {k === "Datasheet" ? (
                <span className="row" style={{ gap: 8 }}>
                  <a className="link" href={v} target="_blank" rel="noreferrer">
                    open →
                  </a>
                  <button
                    type="button"
                    className="btn sm ghost"
                    onClick={() => downloadDatasheet(v)}
                    title="Download and save locally"
                  >
                    download ↓
                  </button>
                </span>
              ) : (
                <span className="mono small">{v}</span>
              )}
            </div>
          ))}
          {part.notes && (
            <div className="mt code-block">{part.notes}</div>
          )}
        </div>

        <div className="card">
          <div className="spread">
            <h2>Reservations</h2>
            <button className="btn sm ghost" onClick={() => setShowReserve(true)}>
              + Reserve
            </button>
          </div>
          {partReservations.length === 0 && <div className="muted small">No active reservations.</div>}
          {partReservations.map((r: Reservation) => (
            <div key={r.id} className="row mb" style={{ justifyContent: "space-between" }}>
              <Link className="link" to={`/projects/${r.project_id}`}>
                {r.project_name}
              </Link>
              <Badge kind="warn">{r.quantity} reserved</Badge>
            </div>
          ))}
          <h2 className="mt">Supplier parts</h2>
          {part.supplier_parts.length === 0 && <div className="muted small">None.</div>}
          {part.supplier_parts.map((sp) => (
            <div key={sp.id} className="row mb" style={{ justifyContent: "space-between" }}>
              <span>
                <strong>{sp.supplier_name}</strong>{" "}
                <span className="mono muted">{sp.supplier_sku}</span>
              </span>
              <span className="small">
                {sp.price !== null && `${sp.currency} ${sp.price}`}
                {sp.stock !== null && ` · ${sp.stock} in stock`}
              </span>
            </div>
          ))}
          <button className="btn sm ghost" onClick={() => setShowSupplier(true)}>
            + Link supplier part
          </button>
        </div>
      </div>

      <div className="grid cols-2 mt">
        <div className="card">
          <h2>Transaction history</h2>
          {partTxns.length === 0 ? (
            <div className="muted small">No transactions.</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>When</th>
                  <th className="num">Δ</th>
                  <th>Location</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {partTxns.map((t) => (
                  <tr key={t.id}>
                    <td className="muted small">{formatDate(t.timestamp)}</td>
                    <td className="num">
                      <Quantity value={t.quantity_change} change={t.quantity_change} />
                    </td>
                    <td className="mono muted small">{t.location_path}</td>
                    <td className="small">{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h2>Attachments</h2>
          <div className="row mb">
            <label className="btn sm ghost" style={{ cursor: "pointer" }}>
              Upload file
              <input type="file" style={{ display: "none" }} onChange={upload} />
            </label>
            {!showUrlFetch ? (
              <button className="btn sm ghost" onClick={() => setShowUrlFetch(true)}>
                Download from URL
              </button>
            ) : (
              <form className="row" style={{ gap: 8 }} onSubmit={fetchFromUrl}>
                <input
                  type="url"
                  placeholder="https://…/datasheet.pdf"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  style={{ flex: 1, minWidth: 200 }}
                  autoFocus
                />
                <button className="btn sm" type="submit">
                  Fetch
                </button>
              </form>
            )}
          </div>
          {(attachments ?? []).length === 0 && <div className="muted small">No attachments.</div>}
          {attachments?.map((a) => (
            <div key={a.id} className="row mb" style={{ justifyContent: "space-between" }}>
              <a
                className="link"
                href={`/api/attachments/${a.id}/download`}
                target="_blank"
                rel="noreferrer"
              >
                {a.filename}
              </a>
              <span className="muted small">
                {a.kind} · {(a.size / 1024).toFixed(1)} KB
              </span>
            </div>
          ))}
        </div>
      </div>

      {showAdjust && <AdjustModal part={part} onClose={() => setShowAdjust(false)} />}

      {showEdit && (
        <Modal title="Edit part" onClose={() => setShowEdit(false)} wide>
          <PartForm initial={part} onSubmit={update} />
        </Modal>
      )}

      {showSupplier && (
        <Modal title="Link supplier part" onClose={() => setShowSupplier(false)}>
          <form onSubmit={addSupplierPart}>
            <div className="field">
              <label>Supplier</label>
              <select name="supplier_id" required>
                {suppliers?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <div className="field">
                <label>SKU</label>
                <input name="supplier_sku" />
              </div>
              <div className="field">
                <label>URL</label>
                <input name="url" />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Price</label>
                <input name="price" type="number" step="0.0001" />
              </div>
              <div className="field">
                <label>Stock</label>
                <input name="stock" type="number" />
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowSupplier(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Link
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showReserve && (
        <Modal title="Reserve stock" onClose={() => setShowReserve(false)}>
          <form onSubmit={reserve}>
            <div className="field">
              <label>Project</label>
              <select name="project_id" required>
                <option value="">Select project…</option>
                {projects?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Quantity (available: {part.available_quantity})</label>
              <input name="quantity" type="number" required min={1} max={part.available_quantity} />
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowReserve(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Reserve
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
