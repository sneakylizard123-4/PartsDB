import { useMemo, useState } from "react";
import { api } from "../api";
import { Modal, errorMessage, useAsync, useToast } from "./ui";

export function MoveLocationModal({
  locationId,
  locationLabel,
  onClose,
  onMoved,
}: {
  locationId: string;
  locationLabel: string;
  onClose: () => void;
  onMoved: () => void;
}) {
  const toast = useToast();
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const { data: locations, loading } = useAsync(() => api.listLocations(), []);

  const options = useMemo(() => {
    const list = locations ?? [];
    const byParent = new Map<string, string[]>();
    for (const l of list) {
      if (l.parent_id) {
        const arr = byParent.get(l.parent_id) ?? [];
        arr.push(l.id);
        byParent.set(l.parent_id, arr);
      }
    }
    const excluded = new Set<string>([locationId]);
    const stack = [locationId];
    while (stack.length) {
      const cur = stack.pop()!;
      for (const child of byParent.get(cur) ?? []) {
        if (!excluded.has(child)) {
          excluded.add(child);
          stack.push(child);
        }
      }
    }
    return list.filter((l) => !excluded.has(l.id));
  }, [locations, locationId]);

  const submit = async () => {
    if (!target) return;
    setBusy(true);
    try {
      await api.moveLocation(locationId, target);
      toast("Location moved");
      onMoved();
      onClose();
    } catch (err) {
      toast(errorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={`Move ${locationLabel}`} onClose={onClose}>
      <p className="muted small mb">
        The whole location and everything inside it (child compartments and all
        of their stock) moves with it.
      </p>
      <div className="field">
        <label>New parent</label>
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          disabled={loading || !locations}
        >
          <option value="">Select new parent…</option>
          {options.map((l) => (
            <option key={l.id} value={l.id}>
              {l.full_path}
            </option>
          ))}
        </select>
      </div>
      <div className="modal-actions">
        <button className="btn ghost" type="button" onClick={onClose}>
          Cancel
        </button>
        <button className="btn" onClick={submit} disabled={busy || !target}>
          {busy ? "Moving…" : "Move"}
        </button>
      </div>
    </Modal>
  );
}