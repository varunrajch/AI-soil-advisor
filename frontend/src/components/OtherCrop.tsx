import { useEffect, useState } from "react";
import { api } from "../api";
import type { Plan, PlanRequest, TextTable } from "../types";
import { BuyList, CostLines } from "./ActionCard";

export function OtherCrop({ req, crops, t }: { req: PlanRequest; crops: string[]; t: TextTable }) {
  const others = crops.filter((c) => c !== req.crop);
  const [crop, setCrop] = useState(others[0]);
  const [plan, setPlan] = useState<Plan | null>(null);

  useEffect(() => {
    if (!others.includes(crop)) setCrop(others[0]);
  }, [req.crop]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let live = true;
    api.plan({ ...req, crop }).then((p) => live && setPlan(p)).catch(() => live && setPlan(null));
    return () => { live = false; };
  }, [JSON.stringify(req), crop]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <details className="panel other">
      <summary>🔁 {t.other_crop}</summary>
      <label className="inline">
        <span>{t.crop}</span>
        <select value={crop} onChange={(e) => setCrop(e.target.value)}>
          {others.map((c) => <option key={c} value={c}>{t.crops[c]}</option>)}
        </select>
      </label>
      {plan && (
        <div className="card small-card">
          <h3>🧪 {t.buy}</h3>
          <BuyList plan={plan} />
          <h3>💰 {t.cost}</h3>
          <CostLines plan={plan} t={t} />
        </div>
      )}
    </details>
  );
}
