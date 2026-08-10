import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import {
  Badge,
  ErrorBox,
  Loading,
  Modal,
  errorMessage,
  useAsync,
  useToast,
} from "../components/ui";

export default function Projects() {
  const toast = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const { data, loading, error, reload } = useAsync(() => api.listProjects(), []);

  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await api.createProject({
        name: String(fd.get("name")),
        description: String(fd.get("description") || "") || undefined,
        build_qty: Number(fd.get("build_qty") || 1),
        status: String(fd.get("status") || "active"),
      });
      toast("Project created");
      setShowCreate(false);
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
          <h1>Projects</h1>
          <div className="sub">{data?.length ?? 0} projects</div>
        </div>
        <div className="actions">
          <button className="btn" onClick={() => setShowCreate(true)}>
            + New project
          </button>
        </div>
      </div>

      <div className="grid cols-3">
        {data?.map((p) => (
          <div key={p.id} className="card">
            <div className="spread">
              <Link className="link" to={`/projects/${p.id}`}>
                <h2 style={{ margin: 0 }}>{p.name}</h2>
              </Link>
              <Badge kind={p.status === "active" ? "ok" : "neutral"}>{p.status}</Badge>
            </div>
            <p className="muted small">
              {p.description || "No description"}
            </p>
            <div className="row">
              <Badge kind="info">×{p.build_qty} build qty</Badge>
            </div>
          </div>
        ))}
        {data?.length === 0 && (
          <div className="card">
            <div className="empty-state" style={{ padding: 20 }}>
              No projects yet.
            </div>
          </div>
        )}
      </div>

      {showCreate && (
        <Modal title="New project" onClose={() => setShowCreate(false)}>
          <form onSubmit={create}>
            <div className="field">
              <label>Name</label>
              <input name="name" required autoFocus placeholder="Mesh Node V2" />
            </div>
            <div className="field">
              <label>Description</label>
              <textarea name="description" rows={2} />
            </div>
            <div className="form-row">
              <div className="field">
                <label>Build quantity</label>
                <input name="build_qty" type="number" defaultValue={1} min={1} />
              </div>
              <div className="field">
                <label>Status</label>
                <select name="status">
                  <option value="active">active</option>
                  <option value="planning">planning</option>
                  <option value="paused">paused</option>
                  <option value="done">done</option>
                </select>
              </div>
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
    </div>
  );
}
