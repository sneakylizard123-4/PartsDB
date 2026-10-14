import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Html5Qrcode } from "html5-qrcode";
import { api } from "../api";
import { errorMessage, useToast } from "../components/ui";

const QR_PATTERN = /\/locations\/([A-Za-z0-9-]+)$/;

export default function Scan() {
  const toast = useToast();
  const navigate = useNavigate();
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const resolving = useRef(false);

  const stop = async () => {
    const scanner = scannerRef.current;
    if (!scanner) return;
    try {
      if (scanner.isScanning) await scanner.stop();
    } catch {
      // camera already released
    }
    scanner.clear();
    scannerRef.current = null;
    setScanning(false);
  };

  const start = async () => {
    setError(null);
    const scanner = new Html5Qrcode("qr-reader");
    scannerRef.current = scanner;
    try {
      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 220, height: 220 } },
        async (decoded) => {
          if (resolving.current) return;
          const m = decoded.trim().match(QR_PATTERN);
          if (!m) {
            toast("That's not a location QR code", "error");
            return;
          }
          resolving.current = true;
          await stop();
          try {
            const loc = await api.getLocation(m[1]);
            navigate(`/locations/${loc.id}`, {
              state: { fromScan: true },
              replace: true,
            });
          } catch (err) {
            resolving.current = false;
            setError(errorMessage(err));
            setScanning(true);
            start();
          }
        },
        () => {}
      );
      setScanning(true);
    } catch (err) {
      scannerRef.current = null;
      setError(errorMessage(err) + " — camera access may be blocked or denied.");
    }
  };

  useEffect(() => {
    start();
    return () => {
      void stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Scan location QR</h1>
          <div className="sub">
            Point the camera at a location label to jump straight to it.
          </div>
        </div>
        <div className="actions">
          <button className="btn ghost" onClick={scanning ? stop : start}>
            {scanning ? "Stop camera" : "Restart camera"}
          </button>
        </div>
      </div>

      <div className="card" style={{ maxWidth: 560 }}>
        <div id="qr-reader" className="qr-reader" />
        {error && <div className="scan-error">{error}</div>}
        {!scanning && !error && (
          <p className="muted small mb">Starting camera…</p>
        )}
        <p className="muted small mb">
          Codes look like <span className="mono">/locations/…</span>. At the
          location you can also post a discrepancy report after a physical
          count.
        </p>
      </div>
    </div>
  );
}