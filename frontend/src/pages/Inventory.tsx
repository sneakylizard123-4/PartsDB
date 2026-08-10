import { Link } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, Loading, Quantity, useAsync } from "../components/ui";

export default function Inventory() {
  const { data, loading, error, reload } = useAsync(() => api.listInventory(), []);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Inventory</h1>
          <div className="sub">
            {data?.length ?? 0} stock entries across all locations
          </div>
        </div>
        <div className="actions">
          <Link className="btn" to="/locations">
            Manage locations
          </Link>
        </div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Part</th>
              <th>Value</th>
              <th>Package</th>
              <th>Manufacturer / MPN</th>
              <th>Location</th>
              <th className="num">Quantity</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((i) => (
              <tr key={i.id}>
                <td>
                  <Link className="link mono" to={`/parts/${i.part_id}`}>
                    {i.part_internal_id || "—"}
                  </Link>
                </td>
                <td>{i.part_value || "—"}</td>
                <td className="mono">{i.part_package || "—"}</td>
                <td className="muted small">
                  {i.part_manufacturer || ""} {i.part_mpn || ""}
                </td>
                <td>
                  <Link className="mono muted small" to={`/locations/${i.location_id}`}>
                    📍 {i.location_path}
                  </Link>
                </td>
                <td className="num">
                  <strong>
                    <Quantity value={i.quantity} />
                  </strong>
                </td>
              </tr>
            ))}
            {data?.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  No inventory yet. Add stock from a part page.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
