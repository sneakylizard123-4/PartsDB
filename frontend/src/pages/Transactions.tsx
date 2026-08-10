import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import {
  ErrorBox,
  Loading,
  Quantity,
  formatDate,
  useAsync,
} from "../components/ui";

export default function Transactions() {
  const [limit, setLimit] = useState(100);
  const { data, loading, error, reload } = useAsync(
    () => api.listTransactions({ limit }),
    [limit]
  );

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Transactions</h1>
          <div className="sub">
            Immutable audit log · {data?.total ?? 0} records
          </div>
        </div>
        <div className="actions">
          <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            {[50, 100, 200, 500].map((n) => (
              <option key={n} value={n}>
                {n} per page
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>When</th>
              <th>Part</th>
              <th className="num">Δ</th>
              <th>Location</th>
              <th>Reason</th>
              <th>Source</th>
              <th>Project</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((t) => (
              <tr key={t.id}>
                <td className="muted">{formatDate(t.timestamp)}</td>
                <td>
                  <Link className="link mono" to={`/parts/${t.part_id}`}>
                    {t.part_internal_id || t.part_value || "—"}
                  </Link>
                </td>
                <td className="num">
                  <Quantity value={t.quantity_change} change={t.quantity_change} />
                </td>
                <td className="mono muted small">{t.location_path}</td>
                <td className="small">{t.reason}</td>
                <td className="muted small">{t.source}</td>
                <td>
                  {t.project_id ? (
                    <Link className="link small" to={`/projects/${t.project_id}`}>
                      open
                    </Link>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
              </tr>
            ))}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={7} className="empty">
                  No transactions yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
