import { useState } from "react";
import { MSL_LEVELS, PACKAGES, PART_CATEGORIES, TOLERANCES } from "../constants";
import type { Part, PartCreate } from "../types";

const FIELDS: {
  key: keyof PartCreate;
  label: string;
  type?: string;
  options?: string[];
}[] = [
  { key: "value", label: "Value" },
  { key: "package", label: "Package", options: PACKAGES },
  { key: "category", label: "Category", options: PART_CATEGORIES },
  { key: "manufacturer", label: "Manufacturer" },
  { key: "mpn", label: "MPN" },
  { key: "lcsc_number", label: "LCSC #" },
  { key: "digikey_number", label: "DigiKey #" },
  { key: "tolerance", label: "Tolerance", options: TOLERANCES },
  { key: "voltage_rating", label: "Voltage rating" },
  { key: "current_rating", label: "Current rating" },
  { key: "msl", label: "MSL", options: MSL_LEVELS },
  { key: "min_qty", label: "Min qty", type: "number" },
  { key: "desired_qty", label: "Desired qty", type: "number" },
  { key: "reorder_qty", label: "Reorder qty", type: "number" },
];

function SelectField({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">— none —</option>
      {value && !options.includes(value) && (
        <option value={value}>{value}</option>
      )}
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

export default function PartForm({
  initial,
  onSubmit,
  busy,
}: {
  initial?: Part;
  onSubmit: (body: PartCreate) => void;
  busy?: boolean;
}) {
  const [form, setForm] = useState<Record<string, string>>(() => {
    const out: Record<string, string> = {};
    for (const f of FIELDS) {
      const v = initial?.[f.key];
      out[f.key as string] = v === null || v === undefined ? "" : String(v);
    }
    out["description"] = initial?.description ?? "";
    out["datasheet_url"] = initial?.datasheet_url ?? "";
    out["notes"] = initial?.notes ?? "";
    return out;
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const build = (): PartCreate => {
    const body: Record<string, unknown> = {};
    for (const f of FIELDS) {
      const raw = form[f.key as string];
      if (f.type === "number") {
        body[f.key as string] = raw === "" ? null : Number(raw);
      } else {
        body[f.key as string] = raw === "" ? null : raw;
      }
    }
    body["description"] = form["description"] === "" ? null : form["description"];
    body["datasheet_url"] = form["datasheet_url"] === "" ? null : form["datasheet_url"];
    body["notes"] = form["notes"] === "" ? null : form["notes"];
    return body as PartCreate;
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(build());
      }}
    >
      <div className="form-row">
        {FIELDS.map((f) => (
          <div className="field" key={String(f.key)}>
            <label>{f.label}</label>
            {f.options ? (
              <SelectField
                value={form[String(f.key)]}
                options={f.options}
                onChange={(v) => set(String(f.key), v)}
              />
            ) : (
              <input
                type={f.type ?? "text"}
                value={form[String(f.key)]}
                onChange={(e) => set(String(f.key), e.target.value)}
                autoFocus={f.key === "value"}
              />
            )}
          </div>
        ))}
      </div>
      <div className="field">
        <label>Description</label>
        <textarea rows={2} value={form["description"]} onChange={(e) => set("description", e.target.value)} />
      </div>
      <div className="field">
        <label>Datasheet URL</label>
        <input value={form["datasheet_url"]} onChange={(e) => set("datasheet_url", e.target.value)} />
      </div>
      <div className="field">
        <label>Notes</label>
        <textarea rows={2} value={form["notes"]} onChange={(e) => set("notes", e.target.value)} />
      </div>
      <div className="modal-actions">
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Saving…" : "Save part"}
        </button>
      </div>
    </form>
  );
}
