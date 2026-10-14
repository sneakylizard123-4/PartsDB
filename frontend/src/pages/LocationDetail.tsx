import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import {
  Badge,
  ErrorBox,
  Loading,
  Modal,
  Quantity,
  errorMessage,
  formatDate,
  useAsync,
  useToast,
} from "../components/ui";
import { MoveLocationModal } from "../components/MoveLocation";

export default function LocationDetail() {
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const navigate = useNavigate();
  const routeLocation = useLocation();
  const fromScan = (routeLocation.state as { fromScan?: boolean } | null)?.fromScan;
  const [showAdd, setShowAdd] = useState(false);
  const [showMove, setShowMove] = useState(false);
  const [showDisc, setShowDisc] = useState(false);
  const [qrVisible, setQrVisible] = useState(false);
  const [allParts, setAllParts] = useState<{ id: string; label: string }[]>([]);
  const [discPart, setDiscPart] = useState("");
  const [discQty, setDiscQty] = useState("");

  const { data, loading, error, reload } = useAsync(
    () => api.locationContents(id!),
    [id]
  );
  const { data: txns } = useAsync(
    () => api.listTransactions({ location_id: id!, limit: 30 }),
    [id]
  );

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;

  const { location, items, children, compartments } = data;

  const adjust = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const partId = String(fd.get("part_id"));
    const qty = Number(fd.get("quantity"));
    const reason = String(fd.get("reason") || "adjustment");
    if (!partId || !qty) return;
    try {
      await api.adjustInventory({
        part_id: partId,
        location_id: location.id,
        quantity_change: qty,
        reason,
      });
      toast("Stock updated");
      setShowAdd(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const removeLocation = async () => {
    if (!confirm(`Delete location ${location.full_path}?`)) return;
    try {
      await api.deleteLocation(location.id);
      toast("Location deleted");
      navigate("/locations");
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const reportDiscrepancy = async () => {
    const qty = Number(discQty);
    if (!discPart || !Number.isFinite(qty) || qty < 0) {
      toast("Pick a part and a non-negative counted quantity", "error");
      return;
    }
    try {
      await api.reportDiscrepancy(location.id, {
        part_id: discPart,
        actual_quantity: qty,
      });
      toast("Discrepancy reported, stock corrected");
      setShowDisc(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const loadParts = async () => {
    const res = await api.listParts({ limit: 200 });
    setAllParts(
      res.items.map((p) => ({
        id: p.id,
        label: `${p.internal_id || "?"} (${p.value || ""} ${p.package || ""})`.trim(),
      }))
    );
  };

  const isCompartment = location.location_type === "compartment";

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="mono">{location.name}</h1>
          <div className="sub">📍 {location.full_path}</div>
          <div className="row mt">
            <Badge kind={isCompartment ? "ok" : "info"}>{location.location_type}</Badge>
            {compartments.length > 0 && <Badge kind="neutral">Organizer compartment</Badge>}
            {fromScan && <Badge kind="warn">Located via QR</Badge>}
          </div>
        </div>
        <div className="actions">
          <button className="btn ghost" onClick={() => { setQrVisible((v) => !v); }}>
            QR code
          </button>
          <button className="btn ghost" onClick={() => setShowMove(true)}>
            Move
          </button>
          <button
            className="btn ghost"
            onClick={() => setShowDisc(true)}
            disabled={items.length === 0}
            title={items.length ? "Correct recorded stock after a count" : "No stock recorded here"}
          >
            Report discrepancy
          </button>
          <button
            className="btn"
            onClick={() => { void loadParts(); setShowAdd(true); }}
            disabled={!isCompartment}
            title={isCompartment ? "" : "Add stock at a compartment"}
          >
            + Add stock
          </button>
          <button className="btn danger" onClick={removeLocation}>
            Delete
          </button>
        </div>
      </div>

      {qrVisible && (
        <div className="card" style={{ maxWidth: 240, marginBottom: 14 }}>
          <div className="qr-box">
            <img src={`/api/locations/${location.id}/qr.png`} alt="QR code" />
            <div className="mono small muted mt">{location.qr_code}</div>
            <div className="small muted">
              Print this label for the physical compartment
            </div>
          </div>
        </div>
      )}

      <div className="grid cols-2">
        <div className="card">
          <h2>Contents ({items.length})</h2>
          {items.length === 0 && <div className="muted">Empty compartment.</div>}
          {items.map((i) => (
            <div key={i.id} className="row mb" style={{ justifyContent: "space-between" }}>
              <div>
                <Link className="link mono" to={`/parts/${i.part_id}`}>
                  {i.internal_id || "?"}
                </Link>
                <div className="muted small">
                  {i.value} {i.package} · {i.manufacturer} {i.mpn}
                </div>
              </div>
              <strong className="num">
                <Quantity value={i.quantity} />
              </strong>
            </div>
          ))}
        </div>

        <div className="card">
          <h2>Child locations ({children.length})</h2>
          {children.map((c) => (
            <Link key={c.id} className="link mono row mb" to={`/locations/${c.id}`}>
              📍 {c.full_path}
            </Link>
          ))}
          {children.length === 0 && <div className="muted">No children.</div>}
          {compartments.length > 0 && (
            <>
              <h2 className="mt">Organizer compartments</h2>
              {compartments.map((c) => (
                <div key={c.id} className="row mb" style={{ justifyContent: "space-between" }}>
                  <span className="mono">{c.label || "—"}</span>
                  {c.part_id && (
                    <Link className="link small" to={`/parts/${c.part_id}`}>
                      view part
                    </Link>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      <div className="card mt">
        <h2>Transaction history for this location</h2>
        {(txns?.items.length ?? 0) === 0 ? (
          <div className="muted">No transactions.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>When</th>
                <th>Part</th>
                <th className="num">Δ</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {txns?.items.map((t) => (
                <tr key={t.id}>
                  <td className="muted small">{formatDate(t.timestamp)}</td>
                  <td>
                    <Link className="link mono" to={`/parts/${t.part_id}`}>
                      {t.part_internal_id || t.part_value}
                    </Link>
                  </td>
                  <td className="num">
                    <Quantity value={t.quantity_change} change={t.quantity_change} />
                  </td>
                  <td className="small">{t.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAdd && (
        <Modal title={`Add stock to ${location.name}`} onClose={() => setShowAdd(false)}>
          <form onSubmit={adjust}>
            <div className="field">
              <label>Part</label>
              <select name="part_id" required>
                <option value="">Select part…</option>
                {allParts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Quantity (+add / −remove)</label>
                <input name="quantity" type="number" required autoFocus placeholder="100" />
              </div>
              <div className="field">
                <label>Reason</label>
                <input name="reason" defaultValue="restock" />
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowAdd(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Apply
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showMove && (
        <MoveLocationModal
          locationId={location.id}
          locationLabel={location.name}
          onClose={() => setShowMove(false)}
          onMoved={reload}
        />
      )}

      {showDisc && (
        <Modal
          title={`Report discrepancy at ${location.name}`}
          onClose={() => setShowDisc(false)}
        >
          <p className="muted small mb">
            Set the recorded quantity to what you actually counted here. A{" "}
            <span className="mono">discrepancy</span> transaction is posted to
            correct the stock.
          </p>
          <div className="field">
            <label>Part</label>
            <select
              value={discPart}
              onChange={(e) => {
                setDiscPart(e.target.value);
                const item = items.find((i) => i.part_id === e.target.value);
                if (item) setDiscQty(String(item.quantity));
              }}
            >
              <option value="">Select part…</option>
              {items.map((i) => (
                <option key={i.id} value={i.part_id}>
                  {i.internal_id || "?"} ({i.value} {i.package}) — currently {i.quantity}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Actual quantity counted</label>
            <input
              type="number"
              min={0}
              value={discQty}
              onChange={(e) => setDiscQty(e.target.value)}
              placeholder="e.g. 8"
            />
          </div>
          <div className="modal-actions">
            <button className="btn ghost" type="button" onClick={() => setShowDisc(false)}>
              Cancel
            </button>
            <button className="btn" onClick={reportDiscrepancy} disabled={!discPart}>
              Report
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
