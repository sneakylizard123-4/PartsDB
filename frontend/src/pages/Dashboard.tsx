import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import {
  Badge,
  EmptyState,
  ErrorBox,
  Loading,
  Modal,
  Quantity,
  Stat,
  formatDate,
  useAsync,
} from "../components/ui";
import type { MissingBomItem, Transaction } from "../types";

export default function Dashboard() {
  const { data, loading, error, reload } = useAsync(() => api.dashboard(), []);
  const [bomDetail, setBomDetail] = useState<MissingBomItem | null>(null);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;

  const d = data;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <div className="sub">
            {d.total_parts} parts · {d.total_quantity.toLocaleString()} total pieces
          </div>
        </div>
        <div className="actions">
          <Link className="btn" to="/parts/new">
            + Add Part
          </Link>
          <Link className="btn ghost" to="/projects">
            Projects
          </Link>
          <Link className="btn ghost" to="/organizers">
            Generate Organizer
          </Link>
        </div>
      </div>

      <div className="stat-grid">
        <Stat label="Total parts" value={d.total_parts} />
        <Stat
          label="Low stock parts"
          value={d.low_stock_parts}
          tone={d.low_stock_parts > 0 ? "warn" : "ok"}
        />
        <Stat
          label="Missing BOM components"
          value={d.missing_bom_components}
          tone={d.missing_bom_components > 0 ? "danger" : "ok"}
        />
        <Stat label="Active projects" value={d.active_projects} />
        <Stat
          label="Shopping requirements"
          value={d.shopping_requirements}
          tone={d.shopping_requirements > 0 ? "warn" : undefined}
        />
        <Stat
          label="Unassigned parts"
          value={d.unassigned_parts}
          tone={d.unassigned_parts > 0 ? "warn" : undefined}
        />
        <Stat label="Empty storage" value={d.empty_storage} />
      </div>

      <div className="card mt">
        <div className="spread">
          <h2>Missing BOM items</h2>
          <span className="small muted">
            Click a row for details · newest first
          </span>
        </div>
        {d.missing_bom_items.length === 0 ? (
          <EmptyState text="No unmatched BOM items" />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Designator</th>
                <th>Part</th>
                <th>BOM</th>
                <th>Project</th>
                <th className="num">Needed</th>
                <th className="num">Available</th>
                <th className="num">Short</th>
              </tr>
            </thead>
            <tbody>
              {d.missing_bom_items.map((item) => (
                <tr
                  key={item.item_id}
                  className="clickable"
                  onClick={() => setBomDetail(item)}
                >
                  <td className="mono">{item.designator}</td>
                  <td>{item.value || item.mpn || "—"}</td>
                  <td>{item.bom_name}</td>
                  <td>{item.project_name}</td>
                  <td className="num">{item.needed}</td>
                  <td className="num">{item.available}</td>
                  <td className="num">
                    <Badge kind={item.shortfall > 0 ? "danger" : "ok"}>
                      {item.shortfall}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="grid cols-2 mt">
        <div className="card">
          <h2>Recent transactions</h2>
          {d.recent_transactions.length === 0 ? (
            <EmptyState text="No transactions yet" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Part</th>
                  <th>Δ</th>
                  <th>Location</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {d.recent_transactions.map((t: Transaction) => (
                  <tr key={t.id}>
                    <td className="muted">{formatDate(t.timestamp)}</td>
                    <td>
                      <Link className="link" to={`/parts/${t.part_id}`}>
                        {t.part_internal_id || t.part_value || "—"}
                      </Link>
                    </td>
                    <td className="num">
                      <Quantity value={t.quantity_change} change={t.quantity_change} />
                    </td>
                    <td className="muted mono small">{t.location_path}</td>
                    <td className="muted">{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div>
          <div className="card">
            <h2>Active reservations</h2>
            {d.recent_reservations.length === 0 ? (
              <EmptyState text="No active reservations" />
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Project</th>
                    <th>Part</th>
                    <th className="num">Qty</th>
                  </tr>
                </thead>
                <tbody>
                  {d.recent_reservations.map((r) => (
                    <tr key={r.id}>
                      <td className="muted">{formatDate(r.created_at)}</td>
                      <td>
                        <Link className="link" to={`/projects/${r.project_id}`}>
                          {r.project_name}
                        </Link>
                      </td>
                      <td className="mono">{r.part_internal_id || r.part_value}</td>
                      <td className="num">{r.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <div className="spread">
              <h2>Empty storage</h2>
              <Badge kind="neutral">{d.empty_storage_count}</Badge>
            </div>
            {d.empty_storage_locations.length === 0 ? (
              <EmptyState text="No empty compartments" />
            ) : (
              <table className="table">
                <tbody>
                  {d.empty_storage_locations.map((loc) => (
                    <tr key={loc.id}>
                      <td>
                        <Link className="link small mono" to={`/locations/${loc.id}`}>
                          {loc.full_path || loc.name}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h2>Actions</h2>
            <div className="grid cols-2">
              <Link className="btn ghost" to="/parts">
                Find Part
              </Link>
              <Link className="btn ghost" to="/inventory">
                Add Inventory
              </Link>
              <Link className="btn ghost" to="/shopping">
                Shopping List
              </Link>
              <Link className="btn ghost" to="/locations">
                Locations
              </Link>
            </div>
            <div className="mt small muted">
              Tip: press <span className="kbd">/</span> anywhere to search
            </div>
          </div>
        </div>
      </div>

      {bomDetail && (
        <Modal
          title={`Missing BOM item · ${bomDetail.designator}`}
          onClose={() => setBomDetail(null)}
          wide
        >
          <div className="row mb">
            <strong>{bomDetail.bom_name}</strong>
            <Link className="link" to={`/projects/${bomDetail.project_id}`}>
              {bomDetail.project_name || "View project"}
            </Link>
          </div>
          <table className="table">
            <tbody>
              <tr>
                <td className="muted">Designator</td>
                <td className="mono">{bomDetail.designator}</td>
              </tr>
              <tr>
                <td className="muted">Value</td>
                <td>{bomDetail.value || "—"}</td>
              </tr>
              <tr>
                <td className="muted">Footprint</td>
                <td className="mono">{bomDetail.footprint || "—"}</td>
              </tr>
              <tr>
                <td className="muted">MPN</td>
                <td className="mono">{bomDetail.mpn || "—"}</td>
              </tr>
              <tr>
                <td className="muted">Manufacturer</td>
                <td>{bomDetail.manufacturer || "—"}</td>
              </tr>
              <tr>
                <td className="muted">Quantity per board</td>
                <td className="num">{bomDetail.qty}</td>
              </tr>
              <tr>
                <td className="muted">Needed</td>
                <td className="num">{bomDetail.needed}</td>
              </tr>
              <tr>
                <td className="muted">Available</td>
                <td className="num">{bomDetail.available}</td>
              </tr>
              <tr>
                <td className="muted">Shortfall</td>
                <td className="num">
                  <Badge kind={bomDetail.shortfall > 0 ? "danger" : "ok"}>
                    {bomDetail.shortfall}
                  </Badge>
                </td>
              </tr>
              {bomDetail.matched_part_id && (
                <tr>
                  <td className="muted">Matched part</td>
                  <td>
                    <Link className="link" to={`/parts/${bomDetail.matched_part_id}`}>
                      {bomDetail.matched_part_id}
                    </Link>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div className="modal-actions">
            <Link
              className="btn sm"
              to={`/projects/${bomDetail.project_id}`}
              onClick={() => setBomDetail(null)}
            >
              Open project
            </Link>
          </div>
        </Modal>
      )}
    </div>
  );
}