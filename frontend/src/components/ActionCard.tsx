import { rupees } from "../strings";
import type { Plan, TextTable } from "../types";

export function CostLines({ plan, t }: { plan: Plan; t: TextTable }) {
  const diff = plan.new_cost - plan.old_cost;
  return (
    <ul className="cost">
      <li>{t.old_cost}: <b>{rupees(plan.old_cost)}</b></li>
      <li>{t.new_cost}: <b>{rupees(plan.new_cost)}</b></li>
      <li className={diff < 0 ? "save" : "extra"}>
        {diff < 0 ? t.save : t.extra}: <b>{rupees(Math.abs(diff))}</b>
      </li>
    </ul>
  );
}

export function BuyList({ plan }: { plan: Plan }) {
  return (
    <ul>
      {[...plan.buy, ...plan.extra_buy].map(([name, amount]) => (
        <li key={name}><b>{name}</b>: {amount}</li>
      ))}
    </ul>
  );
}

export function ActionCard({ plan, t, acres }: { plan: Plan; t: TextTable; acres: number }) {
  return (
    <article className="card">
      <h2 className="headline">🌾 {plan.headline}</h2>
      {plan.headline_detail && <p className="detail">{plan.headline_detail}</p>}

      <h3>🧪 {t.buy} <span className="muted">({t.for_acres.replace("{a}", String(acres))})</span></h3>
      <BuyList plan={plan} />

      <h3>📅 {t.when}</h3>
      <ul>
        {plan.when.map(([stage, what]) => (
          <li key={stage}><b>{stage}</b>: {what}</li>
        ))}
      </ul>

      <h3>🔄 {t.changes}</h3>
      <ul className="changes">
        {plan.changes.map((c) => (
          <li key={c.text}>
            <span className={`tag ${c.action.toLowerCase()}`}>{c.label}</span>
            {c.text}
          </li>
        ))}
      </ul>

      <h3>🌱 {t.fixes}</h3>
      <ul>
        {plan.fixes.map((f) => <li key={f}>{f}</li>)}
      </ul>

      <h3>💰 {t.cost}</h3>
      <CostLines plan={plan} t={t} />

      <p className="foot">{plan.footer}</p>
    </article>
  );
}
