import { useState } from "react";
import { api } from "../api";
import {
  Badge,
  ErrorBox,
  Loading,
  Modal,
  errorMessage,
  storageStatusBadge,
  useAsync,
  useToast,
} from "../components/ui";
import type { Organizer } from "../types";

export default function Organizers() {
  const toast = useToast();
  const [showNew, setShowNew] = useState(false);
  const [editing, setEditing] = useState<Organizer | null>(null);
  const { data, loading, error, reload } = useAsync(
    () => api.listOrganizers(),
    []
  );
  const { data: presets } = useAsync(() => api.organizerPresets(), []);

  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const preset = String(fd.get("preset") || "");
    const body: Record<string, unknown> = {};
    if (preset && presets?.[preset]) {
      const p = presets[preset];
      body.preset = preset;
      body.outer_width = p.outer_width;
      body.outer_depth = p.outer_depth;
      body.outer_height = p.outer_height;
    } else {
      body.outer_width = Number(fd.get("outer_width"));
      body.outer_depth = Number(fd.get("outer_depth"));
      body.outer_height = Number(fd.get("outer_height"));
    }
    try {
      const o = await api.createOrganizer(body);
      toast(`Organizer "${o.name}" generated`);
      setShowNew(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const assign = async (o: Organizer, e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const assignments = o.compartments
      .map((c) => {
        const part = String(fd.get(`part_${c.id}`) || "");
        const label = String(fd.get(`label_${c.id}`) || "");
        return part || label ? { compartment_id: c.id, part_id: part || undefined, label: label || undefined } : null;
      })
      .filter(Boolean) as { compartment_id: string; part_id?: string; label?: string }[];
    try {
      await api.assignOrganizer(o.id, assignments);
      toast("Assignments saved");
      setEditing(null);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const remove = async (o: Organizer) => {
    if (!confirm(`Delete organizer "${o.name}"?`)) return;
    try {
      await api.deleteOrganizer(o.id);
      toast("Deleted");
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
          <h1>Organizers</h1>
          <div className="sub">3D-printable tray layouts</div>
        </div>
        <div className="actions">
          <button className="btn" onClick={() => setShowNew(true)}>
            + Generate
          </button>
        </div>
      </div>

      <div className="grid cols-3">
        {data?.map((o) => (
          <div key={o.id} className="card">
            <div className="spread">
              <strong>{o.name}</strong>
              <Badge kind={o.storage_status === "full" ? "ok" : o.storage_status === "empty" ? "neutral" : "warn"}>
                {storageStatusBadge(o.storage_status)}
              </Badge>
            </div>
            <div className="muted small mt">
              {o.outer_width}×{o.outer_depth}×{o.outer_height}mm · {o.compartments.length}{" "}
              compartments · {o.preset ?? "custom"}
            </div>
            <div className="row mt">
              <a
                className="btn sm ghost"
                href={`/api/organizers/${o.id}/stl`}
                target="_blank"
                rel="noreferrer"
              >
                STL
              </a>
              <button className="btn sm ghost" onClick={() => setEditing(o)}>
                Assign
              </button>
              <button className="btn sm ghost danger" onClick={() => remove(o)}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {showNew && (
        <Modal title="Generate organizer" onClose={() => setShowNew(false)}>
          <form onSubmit={create}>
            <div className="field">
              <label>Preset</label>
              <select name="preset" defaultValue="">
                <option value="">— custom —</option>
                {presets &&
                  Object.entries(presets).map(([name, p]) => (
                    <option key={name} value={name}>
                      {name} ({p.outer_width}×{p.outer_depth}×{p.outer_height}mm,{" "}
                      {Math.round(p.outer_width / p.default_size)}×
                      {Math.round(p.outer_depth / p.default_size)} compartments)
                    </option>
                  ))}
              </select>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Width (mm)</label>
                <input name="outer_width" type="number" defaultValue={200} min={20} />
              </div>
              <div className="field">
                <label>Depth (mm)</label>
                <input name="outer_depth" type="number" defaultValue={200} min={20} />
              </div>
              <div className="field">
                <label>Height (mm)</label>
                <input name="outer_height" type="number" defaultValue={20} min={5} />
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowNew(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Generate
              </button>
            </div>
          </form>
        </Modal>
      )}

      {editing && (
        <Modal title={`Assign · ${editing.name}`} onClose={() => setEditing(null)} wide>
          <form onSubmit={(e) => assign(editing, e)}>
            <div className="grid cols-4" style={{ gap: 8 }}>
              {editing.compartments.map((c) => (
                <div key={c.id} className="field" style={{ marginBottom: 8 }}>
                  <label className="mono small">
                    {c.label || `R${c.row}C${c.col}`}
                  </label>
                  <input
                    name={`part_${c.id}`}
                    placeholder="part ID"
                    defaultValue={c.part_id ?? ""}
                  />
                  <input
                    name={`label_${c.id}`}
                    placeholder="label"
                    defaultValue={c.label ?? ""}
                    style={{ marginTop: 4 }}
                  />
                </div>
              ))}
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setEditing(null)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Save
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
