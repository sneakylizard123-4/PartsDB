import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import {
  Badge,
  ErrorBox,
  Loading,
  Modal,
  Quantity,
  errorMessage,
  matchLevelBadge,
  useAsync,
  useToast,
} from "../components/ui";
import type {
  BOM,
  BOMRevision,
  BomRevisionDiff,
  BomRevisionDiffItem,
  CsvPreview,
  NormalizedBomItem,
} from "../types";

const MAPPABLE = [
  ["designator", "Designator"],
  ["value", "Value"],
  ["footprint", "Footprint"],
  ["mpn", "MPN"],
  ["manufacturer", "Manufacturer"],
  ["qty", "Quantity"],
  ["description", "Description"],
] as const;

function CsvImport({ bomId, onDone }: { bomId: string; onDone: () => void }) {
  const toast = useToast();
  const [stage, setStage] = useState<"upload" | "map" | "importing">("upload");
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const p = await api.previewCsv(file);
      setPreview(p);
      setMapping(p.detected_mapping);
      setStage("map");
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const importRows = async () => {
    if (!preview) return;
    setStage("importing");
    try {
      const items: NormalizedBomItem[] = await api.normalizeCsv(preview.rows, mapping);
      await api.addBomItems(bomId, items);
      toast(`Imported ${items.length} BOM items`);
      onDone();
    } catch (err) {
      toast(errorMessage(err), "error");
      setStage("map");
    }
  };

  if (stage === "upload") {
    return (
      <div className="empty-state" style={{ padding: 20 }}>
        <div className="big">📄</div>
        <p>Upload a KiCad / JLCPCB / DigiKey BOM export (.csv)</p>
        <label className="btn" style={{ cursor: "pointer" }}>
          Choose CSV
          <input type="file" accept=".csv" style={{ display: "none" }} onChange={upload} />
        </label>
      </div>
    );
  }

  if (!preview) return null;

  return (
    <div>
      <div className="small muted mb">
        {preview.total_rows} rows · columns: {preview.headers.join(", ")}
      </div>
      <div className="field">
        <label>Column mapping</label>
        {MAPPABLE.map(([field, label]) => (
          <div key={field} className="row mb">
            <span style={{ width: 120 }} className="muted">
              {label}
            </span>
            <select
              style={{ flex: 1 }}
              value={mapping[field] ?? ""}
              onChange={(e) =>
                setMapping((m) => ({ ...m, [field]: e.target.value || "" }))
              }
            >
              <option value="">— not mapped —</option>
              {preview.headers.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
      <div className="card" style={{ margin: "10px 0", padding: 10 }}>
        <div className="small muted mb">Preview (first {preview.rows.length} rows)</div>
        <div className="code-block">
          {preview.headers.join("\t")}
          {"\n"}
          {preview.rows.slice(0, 6).map((r, i) => (
            <span key={i}>
              {preview.headers.map((h) => r[h] ?? "").join("\t")}
              {"\n"}
            </span>
          ))}
        </div>
      </div>
      <div className="modal-actions">
        <button className="btn ghost" onClick={() => setStage("upload")}>
          Back
        </button>
        <button className="btn" onClick={importRows} disabled={stage === "importing"}>
          {stage === "importing" ? "Importing…" : `Import ${preview.total_rows} rows`}
        </button>
      </div>
    </div>
  );
}

function ReviewMatches({
  bomIds,
  onChanged,
}: {
  bomIds: Set<string>;
  onChanged: () => void;
}) {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => api.listBomReviews(), []);
  const [busy, setBusy] = useState(false);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const items = (data?.items ?? []).filter((i) => bomIds.has(i.bom_id));

  const action = async (fn: () => Promise<unknown>, message: string) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
      toast(message);
      reload();
      onChanged();
    } catch (err) {
      toast(errorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      {items.length === 0 && (
        <div className="muted">No compatible matches waiting for review.</div>
      )}
      {items.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>BOM</th>
              <th>Ref</th>
              <th className="num">Qty</th>
              <th>Value</th>
              <th>Candidates</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.item_id}>
                <td className="small muted">{item.bom_name}</td>
                <td className="mono">{item.designator}</td>
                <td className="num">{item.qty}</td>
                <td>
                  {item.value || "—"}
                  <div className="small muted">
                    {item.footprint || ""}
                    {item.footprint && item.mpn ? " · " : ""}
                    {item.mpn || ""}
                  </div>
                </td>
                <td>
                  {item.candidates.length === 0 && (
                    <span className="muted small">No candidates</span>
                  )}
                  {item.candidates.map((c) => (
                    <div key={c.part_id} className="mb">
                      <div className="row" style={{ alignItems: "center" }}>
                        <Link className="link mono" to={`/parts/${c.part_id}`}>
                          {c.internal_id || c.value || c.mpn}
                        </Link>
                        <Badge kind="info">{c.package || "—"}</Badge>
                        {c.mpn && <span className="mono small muted">{c.mpn}</span>}
                        <button
                          className="btn sm"
                          disabled={busy}
                          onClick={() =>
                            action(
                              () =>
                                api.approveBomMatch(
                                  item.bom_id,
                                  item.item_id,
                                  c.part_id
                                ),
                              "Substitution approved"
                            )
                          }
                        >
                          Accept
                        </button>
                      </div>
                      <div className="small muted">
                        {c.reason} · stock {c.available_quantity ?? "?"}
                      </div>
                    </div>
                  ))}
                  <button
                    className="btn sm ghost danger"
                    disabled={busy}
                    onClick={() =>
                      action(
                        () => api.rejectBomMatch(item.bom_id, item.item_id),
                        "Rejected — needs manual part selection"
                      )
                    }
                  >
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function statusBadge(item: BomRevisionDiffItem) {
  switch (item.status) {
    case "added":
      return <Badge kind="ok">+</Badge>;
    case "removed":
      return <Badge kind="danger">−</Badge>;
    case "changed":
      return <Badge kind="warn">~</Badge>;
    default:
      return <Badge kind="neutral">·</Badge>;
  }
}

function RevisionDiff({ bom }: { bom: BOM }) {
  const {
    data: revisions,
    loading: revLoading,
    error: revError,
    reload: reloadRevs,
  } = useAsync(() => api.listBomRevisions(bom.id), [bom.id]);
  const sorted = [...(revisions ?? [])].sort((a, b) => a.version - b.version);
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");

  const from = fromId || sorted[0]?.id || "";
  const to = toId || sorted[sorted.length - 1]?.id || "";

  const { data, loading, error, reload } = useAsync<BomRevisionDiff | null>(
    async () =>
      from && to && from !== to
        ? api.bomRevisionDiff(bom.id, from, to)
        : null,
    [from, to, bom.id]
  );

  if (revLoading) return <Loading />;
  if (revError) return <ErrorBox message={revError} onRetry={reloadRevs} />;

  const revOption = (r: BOMRevision) => (
    <option key={r.id} value={r.id}>
      {r.version}.{r.comment ? ` ${r.comment}` : ""}
    </option>
  );

  return (
    <div>
      <div className="row mb">
        <div className="field">
          <label>From</label>
          <select value={from} onChange={(e) => setFromId(e.target.value)}>
            {sorted.map(revOption)}
          </select>
        </div>
        <div className="field">
          <label>To</label>
          <select value={to} onChange={(e) => setToId(e.target.value)}>
            {sorted.map(revOption)}
          </select>
        </div>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {!loading && !error && !data && (
        <div className="muted small">Pick two different revisions to compare.</div>
      )}
      {data && (
        <div>
          <div className="row mb">
            {data.items.length > 0 ? (
              <>
                <Badge kind="ok">+{data.summary.added} added</Badge>
                <Badge kind="danger">−{data.summary.removed} removed</Badge>
                <Badge kind="warn">~{data.summary.changed} changed</Badge>
                <Badge kind="neutral">{data.summary.unchanged} unchanged</Badge>
                {data.summary.total_shortfall > 0 && (
                  <Badge kind="danger">
                    short {data.summary.total_shortfall}
                  </Badge>
                )}
              </>
            ) : (
              <span className="muted small">
                {data.bom_name} has no items in these revisions.
              </span>
            )}
          </div>
          <table className="table">
            <thead>
              <tr>
                <th />
                <th>Ref</th>
                <th className="num">Qty</th>
                <th>Part</th>
                <th className="num">Needed (×{data.build_qty})</th>
                <th className="num">Available</th>
                <th className="num">Impact</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.designator}>
                  <td>{statusBadge(item)}</td>
                  <td className="mono">{item.designator}</td>
                  <td className="num">
                    {item.from_item && item.to_item
                      ? `${item.from_item.qty} → ${item.to_item.qty}`
                      : item.status === "removed"
                        ? `−${item.from_item?.qty}`
                        : item.status === "added"
                          ? `+${item.to_item?.qty}`
                          : "—"}
                    {item.qty_change !== 0 && (
                      <Quantity value={item.qty_change} change={item.qty_change} />
                    )}
                  </td>
                  <td>
                    {item.part ? (
                      <Link className="link mono" to={`/parts/${item.part.id}`}>
                        {item.part.internal_id || item.part.value}
                      </Link>
                    ) : (
                      <span className="muted">unmatched</span>
                    )}
                  </td>
                  <td className="num">{item.needed || "—"}</td>
                  <td className="num">{item.available ?? "—"}</td>
                  <td className="num">
                    {item.shortfall > 0 ? (
                      <Badge kind="danger">−{item.shortfall}</Badge>
                    ) : item.status === "removed" ? (
                      <Badge kind="info">frees stock</Badge>
                    ) : (
                      <Badge kind="ok">ok</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const navigate = useNavigate();
  const [showImport, setShowImport] = useState(false);
  const [importBomId, setImportBomId] = useState("");
  const [showBom, setShowBom] = useState(false);
  const [showReserve, setShowReserve] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [diffBomId, setDiffBomId] = useState<string | null>(null);

  const { data: project, loading, error, reload } = useAsync(
    () => api.getProject(id!),
    [id]
  );
  const { data: boms } = useAsync(() => api.listBoms(), []);
  const { data: requirements, reload: reloadReq } = useAsync(
    () => api.projectRequirements(id!),
    [id]
  );
  const { data: reservations } = useAsync(() => api.listReservations("active"), []);
  const { data: parts } = useAsync(() => api.listParts({ limit: 200 }), []);
  const { data: attachments, reload: reloadAtts } = useAsync(
    () => api.listAttachments("project", id!),
    [id]
  );

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!project) return null;

  const projectBoms = (boms ?? []).filter((b) => b.project_id === project.id);
  const projectReservations = (reservations ?? []).filter((r) => r.project_id === project.id);
  const projectBomIds = new Set(projectBoms.map((b) => b.id));
  const diffBom =
    diffBomId !== null ? (boms ?? []).find((b) => b.id === diffBomId) ?? null : null;

  const createBom = async () => {
    try {
      const bom = await api.createBom({ project_id: project.id, name: "Main BOM" });
      toast("BOM created");
      setImportBomId(bom.id);
      setShowImport(true);
      reload();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const match = async (bomId: string) => {
    try {
      const res = await api.matchBom(bomId);
      toast(`Matched ${res.length} items`);
      reload();
      reloadReq();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const reserve = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await api.createReservation({
        project_id: project.id,
        part_id: String(fd.get("part_id")),
        quantity: Number(fd.get("quantity")),
      });
      toast("Reserved");
      setShowReserve(false);
      reload();
      reloadReq();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const updateProject = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await api.updateProject(project.id, {
        name: String(fd.get("name")),
        description: String(fd.get("description") || "") || undefined,
        build_qty: Number(fd.get("build_qty")),
        status: String(fd.get("status")),
      });
      toast("Project updated");
      setShowEdit(false);
      reload();
      reloadReq();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const deleteProject = async () => {
    if (!confirm(`Delete project ${project.name}?`)) return;
    try {
      await api.deleteProject(project.id);
      toast("Project deleted");
      navigate("/projects");
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await api.uploadAttachment("project", project.id, file);
      toast("Attachment uploaded");
      reloadAtts();
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const genShopping = async () => {
    try {
      const sl = await api.generateShoppingList(project.id);
      toast(`Shopping list "${sl.name}" generated`);
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{project.name}</h1>
          <div className="sub">
            {project.description} · build qty ×{project.build_qty}
          </div>
          <div className="row mt">
            <Badge kind={project.status === "active" ? "ok" : "neutral"}>
              {project.status}
            </Badge>
            <Badge kind={projectReservations.length > 0 ? "warn" : "neutral"}>
              {projectReservations.length} reservations
            </Badge>
          </div>
        </div>
        <div className="actions">
          <button className="btn" onClick={createBom}>
            Import BOM
          </button>
          <button className="btn ghost" onClick={() => setShowReserve(true)}>
            Reserve part
          </button>
          <button className="btn ghost" onClick={genShopping}>
            Shopping list
          </button>
          <button className="btn ghost" onClick={() => setShowEdit(true)}>
            Edit
          </button>
          <button className="btn danger" onClick={deleteProject}>
            Delete
          </button>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <div className="spread">
            <h2>Requirements</h2>
            <button className="btn sm ghost" onClick={() => projectBoms.forEach((b) => match(b.id))}>
              Re-run matching
            </button>
          </div>
          {(requirements?.requirements.length ?? 0) === 0 && (
            <div className="muted small">
              No BOM items yet — import a CSV BOM to see what you need.
            </div>
          )}
          <table className="table">
            <thead>
              <tr>
                <th>Part</th>
                <th className="num">Required</th>
                <th className="num">Available</th>
                <th className="num">Reserved</th>
                <th className="num">Missing</th>
              </tr>
            </thead>
            <tbody>
              {requirements?.requirements.map((r, i) => (
                <tr key={i}>
                  <td>
                    {r.part ? (
                      <Link className="link mono" to={`/parts/${r.part.id}`}>
                        {r.part.internal_id || r.part.value}
                      </Link>
                    ) : (
                      <span className="mono muted">
                        {r.items[0]?.designator || "unmatched"}
                      </span>
                    )}
                  </td>
                  <td className="num">{r.required}</td>
                  <td className="num">{r.available}</td>
                  <td className="num muted">{r.reserved}</td>
                  <td className="num">
                    {r.missing > 0 ? (
                      <Badge kind="danger">−{r.missing}</Badge>
                    ) : (
                      <Badge kind="ok">0</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h2>Reservations</h2>
          {projectReservations.length === 0 && <div className="muted small">None.</div>}
          <table className="table">
            <thead>
              <tr>
                <th>Part</th>
                <th className="num">Qty</th>
              </tr>
            </thead>
            <tbody>
              {projectReservations.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link className="link mono" to={`/parts/${r.part_id}`}>
                      {r.part_internal_id || r.part_value}
                    </Link>
                  </td>
                  <td className="num">{r.quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card mt">
        <div className="spread">
          <h2>BOMs</h2>
          <div className="row">
            <button className="btn sm ghost" onClick={() => setShowReview(true)}>
              Review matches
            </button>
            <button className="btn sm ghost" onClick={() => { setShowBom(true); }}>
              Browse BOMs
            </button>
          </div>
        </div>
        {projectBoms.length === 0 && <div className="muted">No BOMs yet.</div>}
        {projectBoms.map((bom) => (
          <div key={bom.id} className="mb">
            <div className="spread">
              <strong>{bom.name}</strong>
              <div className="row">
                <span className="muted small">{bom.items.length} items</span>
                <button className="btn sm ghost" onClick={() => match(bom.id)}>
                  Match
                </button>
                <button className="btn sm ghost" onClick={() => { setDiffBomId(bom.id); }}>
                  Revisions
                </button>
                <button className="btn sm ghost" onClick={() => { setImportBomId(bom.id); setShowImport(true); }}>
                  Add items
                </button>
              </div>
            </div>
            {bom.items.length > 0 && (
              <table className="table">
                <thead>
                  <tr>
                    <th>Ref</th>
                    <th className="num">Qty</th>
                    <th>Value</th>
                    <th>Footprint</th>
                    <th>MPN</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {bom.items.map((item) => (
                    <tr key={item.id}>
                      <td className="mono">{item.designator}</td>
                      <td className="num">{item.qty}</td>
                      <td>{item.value || "—"}</td>
                      <td className="mono muted">{item.footprint || "—"}</td>
                      <td className="mono muted">{item.mpn || "—"}</td>
                      <td>{matchLevelBadge(item.match_level)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </div>

      <div className="card mt">
        <h2>Attachments</h2>
        <div className="row mb">
          <label className="btn sm ghost" style={{ cursor: "pointer" }}>
            Upload
            <input type="file" style={{ display: "none" }} onChange={upload} />
          </label>
        </div>
        {(attachments ?? []).length === 0 && <div className="muted small">None.</div>}
        {attachments?.map((a) => (
          <div key={a.id} className="row mb" style={{ justifyContent: "space-between" }}>
            <a className="link" href={`/api/attachments/${a.id}/download`} target="_blank" rel="noreferrer">
              {a.filename}
            </a>
            <span className="muted small">{(a.size / 1024).toFixed(1)} KB</span>
          </div>
        ))}
      </div>

      {showImport && (
        <Modal title="Import BOM CSV" onClose={() => setShowImport(false)} wide>
          {importBomId ? (
            <CsvImport
              bomId={importBomId}
              onDone={() => {
                setShowImport(false);
                reload();
                reloadReq();
              }}
            />
          ) : (
            <div className="empty-state">
              No BOM yet. <button className="btn sm mt" onClick={createBom}>Create a BOM first</button>
            </div>
          )}
        </Modal>
      )}

      {showBom && (
        <Modal title="All BOMs" onClose={() => setShowBom(false)} wide>
          {(boms ?? []).length === 0 && <div className="muted">No BOMs.</div>}
          {(boms ?? []).map((b) => (
            <div key={b.id} className="row mb" style={{ justifyContent: "space-between" }}>
              <span>
                <strong>{b.name}</strong>
                <span className="muted small"> · {b.items.length} items</span>
              </span>
              <Link className="link small" to={`/projects/${b.project_id}`}>
                open project
              </Link>
            </div>
          ))}
        </Modal>
      )}

      {showReserve && (
        <Modal title="Reserve stock" onClose={() => setShowReserve(false)}>
          <form onSubmit={reserve}>
            <div className="field">
              <label>Part</label>
              <select name="part_id" required>
                <option value="">Select part…</option>
                {parts?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.internal_id || p.value} (avail {p.available_quantity})
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Quantity</label>
              <input name="quantity" type="number" required min={1} />
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowReserve(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Reserve
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showEdit && (
        <Modal title="Edit project" onClose={() => setShowEdit(false)}>
          <form onSubmit={updateProject}>
            <div className="field">
              <label>Name</label>
              <input name="name" defaultValue={project.name} required />
            </div>
            <div className="field">
              <label>Description</label>
              <textarea name="description" rows={2} defaultValue={project.description ?? ""} />
            </div>
            <div className="form-row">
              <div className="field">
                <label>Build qty</label>
                <input name="build_qty" type="number" defaultValue={project.build_qty} min={1} />
              </div>
              <div className="field">
                <label>Status</label>
                <select name="status" defaultValue={project.status}>
                  {["active", "planning", "paused", "done"].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={() => setShowEdit(false)}>
                Cancel
              </button>
              <button className="btn" type="submit">
                Save
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showReview && (
        <Modal title="Review BOM matches" onClose={() => setShowReview(false)} wide>
          <ReviewMatches
            bomIds={projectBomIds}
            onChanged={() => {
              reload();
              reloadReq();
            }}
          />
        </Modal>
      )}

      {diffBom && (
        <Modal
          title={`Revisions — ${diffBom.name}`}
          onClose={() => setDiffBomId(null)}
          wide
        >
          <RevisionDiff bom={diffBom} />
        </Modal>
      )}
    </div>
  );
}
