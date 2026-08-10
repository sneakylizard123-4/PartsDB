import { Link } from "react-router-dom";
import { api } from "../api";
import {
  EmptyState,
  ErrorBox,
  Loading,
  Quantity,
  Stat,
  formatDate,
  useAsync,
} from "../components/ui";
import type { Transaction } from "../types";

export default function Dashboard() {
  const { data, loading, error, reload } = useAsync(() => api.dashboard(), []);

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
                    <th>Project</th>
                    <th>Part</th>
                    <th className="num">Qty</th>
                  </tr>
                </thead>
                <tbody>
                  {d.recent_reservations.map((r) => (
                    <tr key={r.id}>
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
    </div>
  );
}
