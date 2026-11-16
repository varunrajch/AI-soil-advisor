import { useEffect, useState } from "react";
import { api } from "../api";
import type { Explanation, PlanRequest } from "../types";

export function ExplainPanel({ req, w }: { req: PlanRequest; w: Record<string, string> }) {
  const [data, setData] = useState<Explanation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const key = JSON.stringify(req);

  useEffect(() => {
    setData(null);
    setError(null);
  }, [key]);

  const load = async () => {
    setBusy(true);
    setError(null);
    try {
      setData(await api.explain(req));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel explain">
      <button type="button" className="secondary" onClick={load} disabled={busy}>
        💡 {busy ? w.explaining : w.why}
      </button>
      {error && <div className="msg error">{error}</div>}
      {data && (
        <>
          <ul className="points">
            {data.points.map((p, i) => (
              <li key={i}>
                {p.text.replace(/\s*\[\d+\]/g, "")}
                {p.sources.map((s) => (
                  <button key={s} type="button" className="cite" onClick={() => setOpen(open === s ? null : s)}>
                    {s}
                  </button>
                ))}
              </li>
            ))}
          </ul>
          <p className="muted small">{data.generated_by === "llm" ? w.by_llm : w.by_rules}</p>
          {data.citations.length > 0 && (
            <>
              <h3>📚 {w.sources}</h3>
              <ol className="sources">
                {data.citations.map((c) => (
                  <li key={c.id} className={open === c.id ? "open" : ""}>
                    <button type="button" className="link" onClick={() => setOpen(open === c.id ? null : c.id)}>
                      [{c.id}] {c.title}, {w.page} {c.page}
                    </button>
                    {c.url && <> · <a href={c.url} target="_blank" rel="noreferrer">PDF ↗</a></>}
                    {open === c.id && <blockquote>{c.snippet}…</blockquote>}
                  </li>
                ))}
              </ol>
            </>
          )}
        </>
      )}
    </section>
  );
}
