import { useState } from "react";
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

function Suppliers() {
  const toast = useToast();
  const [showNew, setShowNew] = useState(false);
  const { data, loading, error, reload } = useAsync(() => api.listSuppliers(), []);

  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await api.createSupplier({
        name: String(fd.get("name")),
        website: String(fd.get("website") || "") || undefined,
        notes: String(fd.get("notes") || "") || undefined,
      });
      toast("Supplier added");
      setShowNew(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const remove = async (id: string, name: string) => {
    if (!confirm(`Delete supplier ${name}?`)) return;
    try {
      await api.deleteSupplier(id);
      toast("Deleted");
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div className="card">
      <div className="spread">
        <h2>Suppliers</h2>
        <button className="btn sm ghost" onClick={() => setShowNew(true)}>
          + Add
        </button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Website</th>
            <th>Notes</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {data?.map((s) => (
            <tr key={s.id}>
              <td>
                <strong>{s.name}</strong>
              </td>
              <td>
                {s.website && (
                  <a className="link" href={s.website} target="_blank" rel="noreferrer">
                    {s.website.replace(/^https?:\/\//, "")}
                  </a>
                )}
              </td>
              <td className="muted small">{s.notes}</td>
              <td className="num">
                <button className="btn sm ghost danger" onClick={() => remove(s.id, s.name)}>
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {(data ?? []).length === 0 && <div className="muted">No suppliers yet.</div>}

      {showNew && (
        <Modal title="Add supplier" onClose={() => setShowNew(false)}>
          <form onSubmit={create}>
            <div className="field">
              <label>Name</label>
              <input name="name" required autoFocus placeholder="JLCPCB" />
            </div>
            <div className="field">
              <label>Website</label>
              <input name="website" placeholder="https://jlcpcb.com" />
            </div>
            <div className="field">
              <label>Notes</label>
              <textarea name="notes" rows={2} />
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowNew(false)}>
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

function ApiKeys() {
  const toast = useToast();
  const [showNew, setShowNew] = useState(false);
  const [fresh, setFresh] = useState<string | null>(null);
  const { data, loading, error, reload } = useAsync(() => api.listApiKeys(), []);

  const create = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      const k = await api.createApiKey(String(fd.get("name")));
      setFresh(k.key);
      setShowNew(false);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const revoke = async (id: string) => {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    try {
      await api.revokeApiKey(id);
      toast("Key revoked");
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div className="card">
      <div className="spread">
        <h2>API keys</h2>
        <button className="btn sm ghost" onClick={() => setShowNew(true)}>
          + New key
        </button>
      </div>
      {fresh && (
        <div className="notice mb">
          <strong>Copy this key now — it won't be shown again.</strong>
          <div className="code-block">{fresh}</div>
        </div>
      )}
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Created</th>
            <th>Last used</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {data?.map((k) => (
            <tr key={k.id}>
              <td>
                <strong>{k.name}</strong>
              </td>
              <td className="muted small">
                {new Date(k.created_at).toLocaleDateString()}
              </td>
              <td className="muted small">
                {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "never"}
              </td>
              <td>
                <Badge kind={k.is_active ? "ok" : "neutral"}>
                  {k.is_active ? "active" : "revoked"}
                </Badge>
              </td>
              <td className="num">
                {k.is_active && (
                  <button className="btn sm ghost danger" onClick={() => revoke(k.id)}>
                    Revoke
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showNew && (
        <Modal title="New API key" onClose={() => setShowNew(false)}>
          <form onSubmit={create}>
            <div className="field">
              <label>Name</label>
              <input name="name" required autoFocus placeholder="my-script" />
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
        </Modal>
      )}
    </div>
  );
}

function Backup() {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => api.listBackups(), []);

  const create = async () => {
    try {
      const b = await api.createBackup();
      toast(`Backup ${b.filename} created`);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div className="card">
      <div className="spread">
        <h2>Backup</h2>
        <button className="btn" onClick={create}>
          Create backup
        </button>
      </div>
      {(data ?? []).length === 0 && <div className="muted">No backups yet.</div>}
      <table className="table">
        <thead>
          <tr>
            <th>File</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {data?.map((b) => (
            <tr key={b.filename}>
              <td className="mono">{b.filename}</td>
              <td className="muted small">
                {new Date(b.created_at).toLocaleString()}
              </td>
              <td className="num">
                <a
                  className="btn sm ghost"
                  href={`/api/backup/${encodeURIComponent(b.filename)}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Settings() {
  const { data: me } = useAsync(() => api.me(), []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <div className="sub">Suppliers, API access and data</div>
        </div>
      </div>

      {me && (
        <div className="card mb">
          <h2>Account</h2>
          <div className="muted">
            <strong>{me.username}</strong>
            {me.email && <span> · {me.email}</span>}
          </div>
        </div>
      )}

      <div className="stack">
        <Suppliers />
        <ApiKeys />
        <Backup />
      </div>
    </div>
  );
}
