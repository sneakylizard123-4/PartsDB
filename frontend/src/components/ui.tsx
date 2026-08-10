import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError } from "../api";

/* ---------------- Toast system ---------------- */

interface Toast {
  id: number;
  message: string;
  kind: "info" | "error";
}

const ToastContext = createContext<(message: string, kind?: "info" | "error") => void>(
  () => {}
);

let toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string, kind: "info" | "error" = "info") => {
    const id = ++toastId;
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind === "error" ? "error" : ""}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

/* ---------------- Data fetching hook ---------------- */

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(0);

  useEffect(() => {
    const id = ++idRef.current;
    setLoading(true);
    setError(null);
    fn()
      .then((d) => {
        if (id === idRef.current) setData(d);
      })
      .catch((e) => {
        if (id === idRef.current) setError(errorMessage(e));
      })
      .finally(() => {
        if (id === idRef.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, reload: () => setData(null) };
}

/* ---------------- Small components ---------------- */

export function Loading() {
  return <div className="loading">Loading…</div>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="empty-state">
      <div className="big">⚠</div>
      <div>{message}</div>
      {onRetry && (
        <button className="btn ghost mt" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Badge({
  kind,
  children,
}: {
  kind: "ok" | "warn" | "danger" | "info" | "neutral";
  children: ReactNode;
}) {
  return (
    <span className={`badge ${kind}`}>
      <span className="dot" />
      {children}
    </span>
  );
}

export function stockBadge(part: { low_stock: boolean; total_quantity: number }) {
  if (part.total_quantity <= 0)
    return (
      <Badge kind="danger">Out of stock</Badge>
    );
  if (part.low_stock) return <Badge kind="warn">Low stock</Badge>;
  return <Badge kind="ok">In stock</Badge>;
}

export function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: ReactNode;
  tone?: "ok" | "warn" | "danger";
}) {
  return (
    <div className="stat">
      <div className={`value ${tone ?? ""}`}>{value}</div>
      <div className="label">{label}</div>
    </div>
  );
}

export function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className={`modal ${wide ? "wide" : ""}`}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>{title}</h3>
        {children}
      </div>
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty-state">
      <div className="big">📦</div>
      <div>{text}</div>
    </div>
  );
}

export function Quantity({
  value,
  change,
}: {
  value: number;
  change?: number;
}) {
  const color = change !== undefined ? (change >= 0 ? "var(--ok)" : "var(--danger)") : undefined;
  return (
    <span style={{ fontVariantNumeric: "tabular-nums", color }}>
      {change !== undefined && change > 0 ? "+" : ""}
      {value}
    </span>
  );
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function matchLevelBadge(level: string | null) {
  switch (level) {
    case "exact":
      return <Badge kind="ok">Exact</Badge>;
    case "strong":
      return <Badge kind="info">Strong</Badge>;
    case "compatible":
      return <Badge kind="warn">Compatible</Badge>;
    case "manual":
      return <Badge kind="neutral">Manual</Badge>;
    case "none":
      return <Badge kind="danger">Unmatched</Badge>;
    default:
      return <Badge kind="neutral">—</Badge>;
  }
}

export function storageStatusBadge(status: string) {
  switch (status) {
    case "unassigned":
      return <Badge kind="warn">Unassigned</Badge>;
    case "assigned":
      return <Badge kind="info">Assigned</Badge>;
    case "printed":
      return <Badge kind="neutral">Printed</Badge>;
    case "installed":
      return <Badge kind="ok">Installed</Badge>;
    default:
      return <Badge kind="neutral">{status}</Badge>;
  }
}
