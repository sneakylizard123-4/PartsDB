import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { errorMessage, useToast } from "../components/ui";
import PartForm from "../components/PartForm";
import type { PartCreate } from "../types";

export default function NewPart() {
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();

  const create = async (body: PartCreate) => {
    setBusy(true);
    try {
      const part = await api.createPart(body);
      toast("Part created");
      navigate(`/parts/${part.id}`);
    } catch (err) {
      toast(errorMessage(err), "error");
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Add part</h1>
          <div className="sub">All fields optional — fill in what you know.</div>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 760 }}>
        <PartForm onSubmit={create} busy={busy} />
      </div>
    </div>
  );
}
