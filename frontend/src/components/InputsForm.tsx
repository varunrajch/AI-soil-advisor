import { SOIL_LABELS } from "../strings";
import { SOIL_KEYS, type SoilKey, type TextTable } from "../types";

export interface FormState {
  soil: Record<SoilKey, string>;
  crop: string;
  season: string;
  acres: string;
  last: { urea: string; dap: string; mop: string };
}

interface Props {
  t: TextTable;
  form: FormState;
  crops: string[];
  seasons: string[];
  onChange: (form: FormState) => void;
}

export function InputsForm({ t, form, crops, seasons, onChange }: Props) {
  const set = (patch: Partial<FormState>) => onChange({ ...form, ...patch });

  return (
    <>
      <section className="panel">
        <h2>🧪 {t.soil_values}</h2>
        <div className="grid4">
          {SOIL_KEYS.map((k) => (
            <label key={k}>
              <span>{SOIL_LABELS[k]}</span>
              <input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                value={form.soil[k]}
                onChange={(e) => set({ soil: { ...form.soil, [k]: e.target.value } })}
              />
            </label>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>🌱 {t.farm}</h2>
        <div className="grid3">
          <label>
            <span>{t.crop}</span>
            <select value={form.crop} onChange={(e) => set({ crop: e.target.value })}>
              {crops.map((c) => (
                <option key={c} value={c}>{t.crops[c]}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t.season}</span>
            <select value={form.season} onChange={(e) => set({ season: e.target.value })}>
              {seasons.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label>
            <span>{t.acres}</span>
            <input type="number" inputMode="decimal" step="0.5" min="0.1" value={form.acres}
              onChange={(e) => set({ acres: e.target.value })} />
          </label>
        </div>
      </section>

      <section className="panel">
        <h2>🔄 {t.last_season}</h2>
        <div className="grid3">
          {(["urea", "dap", "mop"] as const).map((f) => (
            <label key={f}>
              <span>{t[f]}</span>
              <input type="number" inputMode="decimal" step="0.5" min="0" value={form.last[f]}
                onChange={(e) => set({ last: { ...form.last, [f]: e.target.value } })} />
            </label>
          ))}
        </div>
      </section>
    </>
  );
}
