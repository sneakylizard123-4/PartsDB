import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, getToken } from "../api";
import type { SearchResult } from "../types";

export function SearchBar() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [focused, setFocused] = useState(false);
  const [active, setActive] = useState(0);
  const navigate = useNavigate();
  const timer = useRef<number | undefined>(undefined);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (
        e.key === "/" &&
        document.activeElement !== inputRef.current &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement)
      ) {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === "Escape") {
        setResults(null);
        setFocused(false);
        inputRef.current?.blur();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    window.clearTimeout(timer.current);
    const term = q.trim();
    if (!term) {
      setResults(null);
      return;
    }
    timer.current = window.setTimeout(() => {
      api
        .search(term)
        .then(setResults)
        .catch(() => setResults([]));
    }, 180);
    return () => window.clearTimeout(timer.current);
  }, [q]);

  const navigateTo = (r: SearchResult) => {
    setQ("");
    setResults(null);
    setFocused(false);
    const paths: Record<string, string> = {
      part: `/parts/${r.id}`,
      location: `/locations/${r.id}`,
      project: `/projects/${r.id}`,
      bom: `/projects/${r.id.split("-")[0]}/boms`,
    };
    navigate(paths[r.type]);
  };

  const open = focused && results !== null && q.trim().length > 0;

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!results?.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (a + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (a - 1 + results.length) % results.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const r = results[active];
      if (r) navigateTo(r);
    }
  };

  return (
    <div className="search-wrap">
      <svg
        className="search-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" />
      </svg>
      <input
        ref={inputRef}
        placeholder="Search parts, locations, projects…  ( / )"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setActive(0);
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={onKeyDown}
      />
      {open && (
        <div className="search-dropdown">
          {results.length === 0 && (
            <div className="search-result">
              <span className="s">No matches for “{q}”</span>
            </div>
          )}
          {results.map((r, i) => (
            <button
              key={`${r.type}-${r.id}`}
              className="search-result"
              style={i === active ? { background: "var(--accent-soft)" } : undefined}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => navigateTo(r)}
            >
              <span className={`type-tag ${r.type}`}>{r.type}</span>
              <span className="t">{r.title}</span>
              {r.subtitle && <span className="s"> — {r.subtitle}</span>}
              {r.location_path && (
                <div className="path">📍 {r.location_path}</div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function LoginRedirectGuard({ children }: { children: React.ReactNode }) {
  if (!getToken()) {
    window.location.href = "/login";
    return null;
  }
  return <>{children}</>;
}
