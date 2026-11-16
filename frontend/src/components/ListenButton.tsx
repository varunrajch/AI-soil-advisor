import { useEffect, useState } from "react";
import { api } from "../api";
import type { PlanRequest, TextTable } from "../types";

export function ListenButton({ req, t, w }: { req: PlanRequest; t: TextTable; w: Record<string, string> }) {
  const [url, setUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const key = JSON.stringify(req);

  // A different plan or language needs new audio.
  useEffect(() => {
    setUrl(null);
    setError(null);
  }, [key]);

  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  const listen = async () => {
    setBusy(true);
    setError(null);
    try {
      setUrl(URL.createObjectURL(await api.speak(req)));
    } catch (e) {
      setError(`${t.audio_fail} (${(e as Error).message})`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="listen">
      <button type="button" onClick={listen} disabled={busy}>
        {busy ? w.preparing_audio : t.listen}
      </button>
      {url && <audio controls autoPlay src={url} />}
      {error && <div className="msg warn">{error}</div>}
    </div>
  );
}
