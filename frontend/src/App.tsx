import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { ActionCard } from "./components/ActionCard";
import { ExplainPanel } from "./components/ExplainPanel";
import { InputsForm, type FormState } from "./components/InputsForm";
import { ListenButton } from "./components/ListenButton";
import { OtherCrop } from "./components/OtherCrop";
import { UploadCard } from "./components/UploadCard";
import { WEB_TEXT } from "./strings";
import { SOIL_KEYS, type ExtractResult, type Health, type Lang, type Meta, type Plan, type PlanRequest } from "./types";

const EMPTY_FORM: FormState = {
  soil: { ph: "7.0", ec: "0.5", oc: "0.5", n: "280", p: "15", k: "200", zn: "0.8", b: "0.6" },
  crop: "Paddy",
  season: "Kharif",
  acres: "1",
  last: { urea: "0", dap: "0", mop: "0" },
};

function toRequest(form: FormState, lang: Lang): PlanRequest | null {
  const soil = {} as PlanRequest["soil"];
  for (const k of SOIL_KEYS) {
    const v = parseFloat(form.soil[k]);
    if (Number.isNaN(v)) return null;
    soil[k] = v;
  }
  const num = (s: string) => parseFloat(s) || 0;
  return {
    soil, crop: form.crop, season: form.season, acres: num(form.acres) || 1, lang,
    last: { urea: num(form.last.urea), dap: num(form.last.dap), mop: num(form.last.mop) },
  };
}

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [bootError, setBootError] = useState(false);
  const [lang, setLang] = useState<Lang>("en");
  const [sample, setSample] = useState("None");
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [submitted, setSubmitted] = useState<PlanRequest | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.meta(), api.health()])
      .then(([m, h]) => { setMeta(m); setHealth(h); })
      .catch(() => setBootError(true));
  }, []);

  // Re-render the plan in the new language without re-entering anything.
  const request = useMemo(() => (submitted ? { ...submitted, lang } : null), [submitted, lang]);

  useEffect(() => {
    if (!request) return;
    let live = true;
    setBusy(true);
    setError(null);
    api.plan(request)
      .then((p) => live && setPlan(p))
      .catch((e) => live && setError(e.message))
      .finally(() => live && setBusy(false));
    return () => { live = false; };
  }, [JSON.stringify(request)]); // eslint-disable-line react-hooks/exhaustive-deps

  const w = WEB_TEXT[lang];
  if (bootError) return <div className="boot msg error">{WEB_TEXT.en.api_down}</div>;
  if (!meta) return <div className="boot">🌾</div>;
  const t = meta.text[lang];

  const loadSample = (name: string) => {
    setSample(name);
    const s = meta.samples[name];
    if (!s) return;
    setForm({
      soil: Object.fromEntries(SOIL_KEYS.map((k) => [k, String(s[k])])) as FormState["soil"],
      crop: s.crop, season: s.season, acres: String(s.acres),
      last: { urea: String(s.last_urea), dap: String(s.last_dap), mop: String(s.last_mop) },
    });
    setSubmitted(null);
    setPlan(null);
  };

  const fromCard = (r: ExtractResult) => {
    const soil = { ...form.soil };
    for (const k of SOIL_KEYS) if (r.values[k] !== null) soil[k] = String(r.values[k]);
    const { crop, season, acres } = r.farm;
    setForm({
      ...form,
      soil,
      crop: crop ?? form.crop,
      season: season ?? form.season,
      acres: acres !== null ? String(acres) : form.acres,
    });
    setSample("None");  // the form no longer matches a sample
    setSubmitted(null);
    setPlan(null);
  };

  const makePlan = () => {
    const req = toRequest(form, lang);
    if (!req) return setError(w.fill_all);
    setSubmitted(req);
  };

  return (
    <div className="app">
      <header>
        <div>
          <h1>🌾 Nela Mitra <span className="te">(నేల మిత్ర)</span></h1>
          <p className="muted">Soil Health Card to action{lang === "te" ? ` · ${t.subtitle}` : ""}</p>
        </div>
        <div className="controls">
          <div className="toggle" role="group" aria-label="Language">
            <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>English</button>
            <button className={lang === "te" ? "on" : ""} onClick={() => setLang("te")}>తెలుగు</button>
          </div>
          <select value={sample} onChange={(e) => loadSample(e.target.value)} aria-label={t.load_sample}>
            <option value="None">{t.load_sample}: {t.none}</option>
            {Object.entries(meta.samples).map(([name, s]) => (
              <option key={name} value={name}>{name}: {s.desc}</option>
            ))}
          </select>
        </div>
      </header>

      <main>
        <div className="col">
          <UploadCard t={t} w={w} enabled={!!health?.ocr_enabled} onRead={fromCard} />
          <InputsForm t={t} form={form} crops={meta.crops} seasons={meta.seasons} onChange={setForm} />
          <button className="primary" onClick={makePlan} disabled={busy}>
            {busy ? w.making : t.make_plan}
          </button>
          {error && <div className="msg error">{error}</div>}
        </div>

        <div className="col">
          {plan && request && (
            <>
              <ActionCard plan={plan} t={t} acres={request.acres} />
              <ListenButton req={request} t={t} w={w} />
              <ExplainPanel req={request} w={w} />
              <OtherCrop req={request} crops={meta.crops} t={t} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
