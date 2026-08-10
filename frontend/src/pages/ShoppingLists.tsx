import { useState } from "react";
import { api } from "../api";
import {
  Badge,
  ErrorBox,
  Loading,
  Modal,
  Quantity,
  errorMessage,
  useAsync,
  useToast,
} from "../components/ui";

export default function ShoppingLists() {
  const toast = useToast();
  const [selected, setSelected] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [showItem, setShowItem] = useState(false);
  const { data, loading, error, reload } = useAsync(
    () => api.listShoppingLists(),
    []
  );
  const { data: projects } = useAsync(() => api.listProjects(), []);

  const active = data?.find((l) => l.id === selected) ?? data?.[0] ?? null;

  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      const sl = await api.createShoppingList(String(fd.get("name") || "Shopping List"));
      toast("List created");
      setShowNew(false);
      setSelected(sl.id);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const generate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const projectId = String(fd.get("project_id") || "");
    try {
      const sl = await api.generateShoppingList(projectId || undefined);
      toast(`Generated "${sl.name}"`);
      setShowNew(false);
      setSelected(sl.id);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const addItem = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!active) return;
    const fd = new FormData(e.currentTarget);
    try {
      await api.addShoppingItem(active.id, {
        part_id: String(fd.get("part_id") || "") || undefined,
        description: String(fd.get("description") || "") || undefined,
        quantity: Number(fd.get("quantity") || 1),
        notes: String(fd.get("notes") || "") || undefined,
      });
      toast("Item added");
      setShowItem(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const removeItem = async (itemId: string) => {
    if (!active) return;
    if (!confirm("Remove this item?")) return;
    try {
      await api.removeShoppingItem(active.id, itemId);
      toast("Removed");
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const removeList = async (id: string) => {
    if (!confirm("Delete this shopping list?")) return;
    try {
      await api.deleteShoppingList(id);
      toast("List deleted");
      if (selected === id) setSelected(null);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const openCount = (data ?? []).filter((l) => l.status === "open").length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Shopping Lists</h1>
          <div className="sub">{openCount} open</div>
        </div>
        <div className="actions">
          <button className="btn" onClick={() => setShowNew(true)}>
            + New list
          </button>
        </div>
      </div>

      <div className="row gap">
        {(data ?? []).map((l) => (
          <button
            key={l.id}
            className={`card selectable ${selected === l.id || active?.id === l.id ? "selected" : ""}`}
            onClick={() => setSelected(l.id)}
          >
            <div className="spread">
              <strong>{l.name}</strong>
              <Badge kind={l.status === "open" ? "ok" : "neutral"}>{l.status}</Badge>
            </div>
            <div className="muted small mt">
              {l.items.length} items ·{" "}
              {l.items.reduce((n, i) => n + i.quantity, 0)} pcs ·{" "}
              {new Date(l.created_at).toLocaleDateString()}
            </div>
          </button>
        ))}
        {(data ?? []).length === 0 && <div className="muted">No shopping lists yet.</div>}
      </div>

      {active && (
        <div className="card mt">
          <div className="spread">
            <h2>{active.name}</h2>
            <div className="actions">
              <button className="btn sm ghost" onClick={() => setShowItem(true)}>
                Add item
              </button>
              <button className="btn sm danger" onClick={() => removeList(active.id)}>
                Delete
              </button>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Item</th>
                <th className="num">Qty</th>
                <th>Status</th>
                <th>Notes</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {active.items.map((i) => (
                <tr key={i.id}>
                  <td>
                    <span className="mono">{i.part_internal_id || i.part_value || "—"}</span>
                    {i.description && <div className="muted small">{i.description}</div>}
                  </td>
                  <td className="num">
                    <Quantity value={i.quantity} />
                  </td>
                  <td>
                    <Badge kind={i.status === "fulfilled" ? "ok" : i.status === "in_cart" ? "warn" : "neutral"}>
                      {i.status}
                    </Badge>
                  </td>
                  <td className="muted small">{i.notes}</td>
                  <td className="num">
                    <button className="btn sm ghost" onClick={() => removeItem(i.id)}>
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <Modal title="New shopping list" onClose={() => setShowNew(false)}>
          <form onSubmit={create}>
            <div className="field">
              <label>Name</label>
              <input name="name" placeholder="Tayda order 42" autoFocus />
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowNew(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Create
              </button>
            </div>
          </form>
          <hr />
          <form onSubmit={generate}>
            <div className="field">
              <label>Generate from project</label>
              <select name="project_id">
                <option value="">— all projects —</option>
                {projects?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="muted small mb">
              Generates a list from BOM requirements for the chosen project (or all open
              projects).
            </div>
            <div className="modal-actions">
              <button className="btn" type="submit">
                Generate
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showItem && active && (
        <Modal title="Add item" onClose={() => setShowItem(false)}>
          <form onSubmit={addItem}>
            <div className="field">
              <label>Part (optional)</label>
              <input name="part_id" placeholder="internal ID or MPN" />
            </div>
            <div className="field">
              <label>Description</label>
              <input name="description" placeholder="e.g. 24 AWG silicone wire, red" />
            </div>
            <div className="field">
              <label>Quantity</label>
              <input name="quantity" type="number" defaultValue={1} min={1} />
            </div>
            <div className="field">
              <label>Notes</label>
              <input name="notes" />
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowItem(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Add
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
