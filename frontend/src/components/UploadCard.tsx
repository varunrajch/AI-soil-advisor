import { useRef, useState } from "react";
import { api } from "../api";
import { SOIL_LABELS } from "../strings";
import type { ExtractResult, TextTable } from "../types";

interface Props {
  t: TextTable;
  w: Record<string, string>;
  enabled: boolean;
  onRead: (result: ExtractResult) => void;
}

// Messages keep their key, not their text, so they follow a language switch.
type Status = { kind: "ok" | "warn" | "error"; key?: string; text?: string; names?: string } | null;

export function UploadCard({ t, w, enabled, onRead }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status[]>([]);
  const input = useRef<HTMLInputElement>(null);

  if (!enabled) {
    return <div className="note">{t.no_key}</div>;
  }

  const render = (s: NonNullable<Status>) => {
    if (!s.key) return s.text;
    const base = String(t[s.key]).replace("{names}", s.names ?? "");
    return s.text ? `${base}: ${s.text}` : base;
  };

  const choose = (f: File | null) => {
    setFile(f);
    setStatus([]);
    setPreview(f ? URL.createObjectURL(f) : null);
  };

  const read = async () => {
    if (!file) return;
    setBusy(true);
    setStatus([]);
    try {
      const result = await api.extract(file);
      if (!result.is_soil_health_card) {
        setStatus([{ kind: "warn", key: "not_card" }]);
        return;
      }
      onRead(result);
      const msgs: Status[] = [{ kind: "ok", key: "read_ok" }];
      if (result.farm.crop || result.farm.season || result.farm.acres !== null) {
        msgs.push({ kind: "warn", key: "read_farm" });
      }
      if (result.missing.length) {
        const names = result.missing.map((k) => SOIL_LABELS[k]).join(", ");
        msgs.push({ kind: "warn", key: "read_missing", names });
      }
      result.warnings.forEach((text) => msgs.push({ kind: "warn", text }));
      setStatus(msgs);
    } catch (e) {
      setStatus([{ kind: "error", key: "read_fail", text: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <h2>📷 {t.upload}</h2>
      <div className="upload-row">
        <button className="secondary" type="button" onClick={() => input.current?.click()}>
          {w.choose_file}
        </button>
        <span className="muted">{file ? file.name : w.upload_hint}</span>
        <input
          ref={input}
          type="file"
          accept="image/png,image/jpeg"
          hidden
          onChange={(e) => choose(e.target.files?.[0] ?? null)}
        />
      </div>
      {preview && <img className="preview" src={preview} alt="" />}
      {file && (
        <button type="button" onClick={read} disabled={busy}>
          {busy ? t.reading : t.read_card}
        </button>
      )}
      {status.map((s, i) => s && <div key={i} className={`msg ${s.kind}`}>{render(s)}</div>)}
    </section>
  );
}
