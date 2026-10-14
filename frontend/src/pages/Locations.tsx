import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import {
  ErrorBox,
  Loading,
  Modal,
  errorMessage,
  useAsync,
  useToast,
} from "../components/ui";
import { MoveLocationModal } from "../components/MoveLocation";
import type { LocationTreeNode } from "../types";

function TreeNode({
  node,
  onAdd,
  onMove,
  expandAll,
}: {
  node: LocationTreeNode;
  onAdd: (parentId: string) => void;
  onMove: (node: LocationTreeNode) => void;
  expandAll: boolean;
}) {
  const [open, setOpen] = useState(expandAll);
  const hasChildren = node.children.length > 0;
  const isCompartment = node.location_type === "compartment";
  return (
    <li>
      <div className="node-row">
        {hasChildren ? (
          <button className="toggle" onClick={() => setOpen((o) => !o)}>
            {open ? "▾" : "▸"}
          </button>
        ) : (
          <span className="toggle" />
        )}
        <svg className="loc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 1 1 16 0zm-5 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0z" />
        </svg>
        <Link className="link" to={`/locations/${node.id}`}>
          {node.name}
        </Link>
        {isCompartment && <span className="badge neutral">compartment</span>}
        <span style={{ flex: 1 }} />
        <button className="btn sm ghost" onClick={() => onMove(node)}>
          move
        </button>
        <button className="btn sm ghost" onClick={() => onAdd(node.id)}>
          + child
        </button>
      </div>
      {hasChildren && open && (
        <ul>
          {node.children.map((c) => (
            <TreeNode key={c.id} node={c} onAdd={onAdd} onMove={onMove} expandAll={expandAll} />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function Locations() {
  const toast = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const [showGrid, setShowGrid] = useState(false);
  const [parentId, setParentId] = useState<string | null>(null);
  const [gridParentId, setGridParentId] = useState<string>("");
  const [gridRows, setGridRows] = useState(2);
  const [gridCols, setGridCols] = useState(4);
  const [expandAll, setExpandAll] = useState(false);
  const [moving, setMoving] = useState<LocationTreeNode | null>(null);
  const { data: tree, loading, error, reload } = useAsync(() => api.locationTree(), []);
  const { data: all } = useAsync(() => api.listLocations(), []);

  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body = {
      name: String(fd.get("name")),
      location_type: String(fd.get("location_type") || "compartment"),
      parent_id: parentId,
      notes: String(fd.get("notes") || "") || undefined,
    };
    try {
      await api.createLocation(body);
      toast("Location created");
      setShowCreate(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const createGrid = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body = {
      name: String(fd.get("name")),
      parent_id: gridParentId || null,
      rows: Number(fd.get("rows")) || 1,
      cols: Number(fd.get("cols")) || 1,
      notes: String(fd.get("notes") || "") || undefined,
    };
    try {
      const cells = await api.createDrawerGrid(body);
      toast(`Created drawer with ${cells.length} compartments`);
      setShowGrid(false);
      setGridParentId("");
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Locations</h1>
          <div className="sub">
            Racks → bins → compartments. One part type per compartment.
          </div>
        </div>
        <div className="actions">
          <button className="btn ghost" onClick={() => setExpandAll((v) => !v)}>
            {expandAll ? "Collapse all" : "Expand all"}
          </button>
          <button className="btn" onClick={() => setShowGrid(true)}>
            + Drawer grid
          </button>
          <button className="btn" onClick={() => { setParentId(null); setShowCreate(true); }}>
            + New top-level location
          </button>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Storage tree</h2>
          <div className="tree">
            {(tree ?? []).length === 0 && <div className="muted">No locations yet.</div>}
            <ul>
              {tree?.map((n) => (
                <TreeNode key={n.id} node={n} onAdd={(pid) => { setParentId(pid); setShowCreate(true); }} onMove={setMoving} expandAll={expandAll} />
              ))}
            </ul>
          </div>
        </div>
        <div className="card">
          <h2>All locations</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Path</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {all?.map((l) => (
                <tr key={l.id}>
                  <td>
                    <Link className="link mono" to={`/locations/${l.id}`}>
                      {l.name}
                    </Link>
                  </td>
                  <td className="mono muted small">{l.full_path}</td>
                  <td className="muted small">{l.location_type}</td>
                </tr>
              ))}
              {all?.length === 0 && (
                <tr>
                  <td colSpan={3} className="empty">
                    No locations. Create your first rack.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <Modal title={parentId ? "Add child location" : "Add location"} onClose={() => setShowCreate(false)}>
          <form onSubmit={create}>
            {parentId && (
              <div className="mb small muted">
                Parent:{" "}
                <span className="mono">{all?.find((l) => l.id === parentId)?.full_path}</span>
              </div>
            )}
            <div className="field">
              <label>Name</label>
              <input name="name" required autoFocus placeholder={parentId ? "A6" : "Rack 1"} />
            </div>
            <div className="field">
              <label>Type</label>
              <select name="location_type" defaultValue={parentId ? "compartment" : "rack"}>
                <option value="rack">Rack</option>
                <option value="bin">Bin</option>
                <option value="compartment">Compartment</option>
                <option value="drawer">Drawer</option>
                <option value="box">Box</option>
              </select>
            </div>
            <div className="field">
              <label>Notes</label>
              <input name="notes" />
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowCreate(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Create
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showGrid && (
        <Modal
          title="Create drawer grid"
          onClose={() => setShowGrid(false)}
        >
          <p className="muted small">
            Bulk-create a drawer and a rows×cols grid of compartments (A1, A2, …) in one step.
          </p>
          <form onSubmit={createGrid}>
            <div className="field">
              <label>Drawer name</label>
              <input name="name" required autoFocus placeholder="BOM trace drawer 1" />
            </div>
            <div className="field">
              <label>Parent (optional)</label>
              <select
                value={gridParentId}
                onChange={(e) => setGridParentId(e.target.value)}
              >
                <option value="">— top level —</option>
                {(all ?? []).map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.full_path}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid cols-2">
              <div className="field">
                <label>Rows</label>
                <input
                  type="number"
                  min={1}
                  max={26}
                  value={gridRows}
                  onChange={(e) => setGridRows(Math.max(1, Number(e.target.value)))}
                  name="rows"
                />
              </div>
              <div className="field">
                <label>Columns</label>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={gridCols}
                  onChange={(e) => setGridCols(Math.max(1, Number(e.target.value)))}
                  name="cols"
                />
              </div>
            </div>
            <div className="field">
              <label>Notes</label>
              <input name="notes" />
            </div>
            <div className="mb small muted">
              {gridRows}×{gridCols} = {gridRows * gridCols} compartments:
            </div>
            <div className="cell-preview">
              {Array.from({ length: gridRows }).map((_, r) => (
                <div key={r} className="cell-preview-row">
                  {Array.from({ length: gridCols }).map((_, c) => (
                    <span key={c} className="cell-preview-cell mono">
                      {String.fromCharCode(65 + r)}
                      {c + 1}
                    </span>
                  ))}
                </div>
              ))}
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowGrid(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Create {gridRows * gridCols} compartments
              </button>
            </div>
          </form>
        </Modal>
      )}

      {moving && (
        <MoveLocationModal
          locationId={moving.id}
          locationLabel={moving.name}
          onClose={() => setMoving(null)}
          onMoved={reload}
        />
      )}
    </div>
  );
}
