import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../api";
import { errorMessage, useToast } from "../components/ui";

export default function Login() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(username, password);
      setToken(res.access_token);
      toast("Signed in");
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="logo">
          <svg viewBox="0 0 32 32" width="30" height="30" fill="none">
            <rect width="32" height="32" rx="6" fill="#2f6df6" />
            <path
              d="M9 16a7 7 0 0 1 14 0v5a2 2 0 0 1-2 2h-2.5v-7a2.5 2.5 0 0 0-5 0v7H11a2 2 0 0 1-2-2z"
              fill="#fff"
            />
          </svg>
          PartsDB
        </div>
        {error && <div className="login-error">{error}</div>}
        <div className="field">
          <label>Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
        </div>
        <div className="field">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button className="btn lg" disabled={busy} style={{ width: "100%" }}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
