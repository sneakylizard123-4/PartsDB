import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { setToken, getToken } from "../api";
import { SearchBar } from "./SearchBar";
import { Modal } from "./ui";

const Icon = ({ d }: { d: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
    <path d={d} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const NAV = [
  { to: "/", label: "Dashboard", icon: "M3 13h8V3H3zm0 8h8v-6H3zm10 0h8V11h-8zM13 3v6h8V3z", end: true },
  { to: "/parts", label: "Parts", icon: "M20.6 6.6 12 2 3.4 6.6v10.8L12 22l8.6-4.6zm0 0L12 11m8.6-4.4L12 11m0 0v11M3.4 6.6 12 11", end: false },
  { to: "/import", label: "Import", icon: "M12 3v12m0 0 4-4m-4 4-4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2", end: false },
  { to: "/inventory", label: "Inventory", icon: "M12 3v18M5 8l14-3m-7 7 7-2M5 16l14 2", end: false },
  { to: "/locations", label: "Locations", icon: "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 1 1 16 0zm-5 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0z", end: false },
  { to: "/scan", label: "Scan QR", icon: "M3 8V5a2 2 0 0 1 2-2h3m8 0h3a2 2 0 0 1 2 2v3m0 8v3a2 2 0 0 1-2 2h-3m-8 0H5a2 2 0 0 1-2-2v-3m4-1h.01M9 12h.01M11 12h.01M13 12h.01M15 12h.01M17 12h.01M12 8v.01", end: false },
  { to: "/transactions", label: "Transactions", icon: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01", end: false },
  { to: "/projects", label: "Projects", icon: "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zm2-2v10m6-8v6M9 11h2m2-3h2m-4 6h4m-2 2v-1", end: false },
  { to: "/shopping", label: "Shopping List", icon: "M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4zm0 0h12M3 6h18M16 10a4 4 0 1 1-8 0", end: false },
  { to: "/organizers", label: "Organizers", icon: "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16zM12 22V12m0 0L3.5 7.5M12 12l8.5-4.5", end: false },
  { to: "/ai", label: "AI Assistant", icon: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 5a2 2 0 1 1 0 4 2 2 0 0 1 0-4zm3 10H9a1 1 0 0 1 0-2h1v-3a1 1 0 0 1 2 0v3h1a1 1 0 0 1 0 2z", end: false },
  { to: "/settings", label: "Settings", icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm7.4-3a7.4 7.4 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7.5 7.5 0 0 0-2-1.2L14.5 3h-5l-.4 2.6a7.5 7.5 0 0 0-2 1.2l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.4l-2 1.6 2 3.4 2.4-1a7.5 7.5 0 0 0 2 1.2l.4 2.6h5l.4-2.6a7.5 7.5 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.1-.4.1-.8.1-1.2z", end: false },
];

function Logo() {
  return (
    <svg viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="6" fill="#2f6df6" />
      <path
        d="M9 16a7 7 0 0 1 14 0v5a2 2 0 0 1-2 2h-2.5v-7a2.5 2.5 0 0 0-5 0v7H11a2 2 0 0 1-2-2z"
        fill="#fff"
      />
    </svg>
  );
}

const SHORTCUTS: { keys: string; desc: string }[] = [
  { keys: "/", desc: "Focus the global part search" },
  { keys: "Ctrl+K", desc: "Focus the global part search" },
  { keys: "N", desc: "Add a new part" },
  { keys: "G then L", desc: "Go to locations" },
  { keys: "G then P", desc: "Go to parts" },
  { keys: "?", desc: "Show this shortcut help" },
];

export default function Layout() {
  const navigate = useNavigate();
  const [helpOpen, setHelpOpen] = useState(false);
  const gotoRef = useRef("");
  const logout = () => {
    setToken(null);
    navigate("/login");
  };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      if (
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        target?.isContentEditable
      ) {
        return;
      }
      if (e.key === "?") {
        e.preventDefault();
        setHelpOpen((v) => !v);
        return;
      }
      if (e.key === "g" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        gotoRef.current = "g";
        window.setTimeout(() => {
          gotoRef.current = "";
        }, 1500);
        return;
      }
      if (gotoRef.current === "g") {
        if (e.key === "l") {
          gotoRef.current = "";
          navigate("/locations");
          return;
        }
        if (e.key === "p") {
          gotoRef.current = "";
          navigate("/parts");
          return;
        }
      }
      if (e.ctrlKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        document.querySelector<HTMLInputElement>(".search-wrap input")?.focus();
        return;
      }
      if (e.key === "/") {
        e.preventDefault();
        document.querySelector<HTMLInputElement>(".search-wrap input")?.focus();
        return;
      }
      if (e.key.toLowerCase() === "n" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        navigate("/parts/new");
        return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Logo />
          PartsDB
        </div>
        <div className="section-label">Workshop</div>
        {NAV.slice(0, 6).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
            <Icon d={n.icon} />
            {n.label}
          </NavLink>
        ))}
        <div className="section-label">Planning</div>
        {NAV.slice(6, -1).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
            <Icon d={n.icon} />
            {n.label}
          </NavLink>
        ))}
        <div className="section-label">System</div>
        {NAV.slice(-1).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
            <Icon d={n.icon} />
            {n.label}
          </NavLink>
        ))}
        <div style={{ flex: 1 }} />
        <button className="btn ghost sm" onClick={logout} style={{ width: "100%" }}>
          Sign out
        </button>
      </aside>
      <div className="main">
        <div className="topbar">
          <SearchBar />
          <div className="spacer" />
          <button className="btn ghost sm kbd-hint" onClick={() => setHelpOpen(true)} title="Keyboard shortcuts">
            <kbd>?</kbd>
          </button>
          {getToken() && (
            <NavLink to="/settings" className="link small">
              <Icon d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16zm0-5a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />
            </NavLink>
          )}
        </div>
        <div className="page">
          <Outlet />
        </div>
      </div>

      {helpOpen && (
        <Modal title="Keyboard shortcuts" onClose={() => setHelpOpen(false)}>
          <table className="table">
            <tbody>
              {SHORTCUTS.map((s) => (
                <tr key={s.keys}>
                  <td>
                    <kbd>{s.keys}</kbd>
                  </td>
                  <td className="muted">{s.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Modal>
      )}
    </div>
  );
}
